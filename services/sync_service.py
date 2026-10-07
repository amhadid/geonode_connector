"""
sync_service.py

Service untuk pemantauan perubahan dan sinkronisasi dataset antara QGIS dan GeoNode/GeoServer.

Responsibilities:
-----------------
- Memantau perubahan lokal pada layer yang sedang diedit (editBuffer: Tambah, Ubah, Hapus)
- Menjalankan proses commit WFS-T ke GeoServer / GeoNode
- Menangani rollback / pembatalan perubahan lokal
- Menyediakan statistik dan riwayat perubahan nyata
"""

from __future__ import annotations

import base64
import os
import re
import subprocess
import urllib.request
import urllib.parse
from datetime import datetime
from typing import Dict, Any, List, Optional, Set

from qgis.core import QgsVectorLayer, QgsFeature, QgsGeometry, QgsFeatureRequest
from qgis.PyQt.QtCore import QVariant

from ..models.service_result import ServiceResult
from ..models.session import session
from ..utils.config import (
    GEOSERVER_ADMIN_USER,
    GEOSERVER_ADMIN_PASSWORD,
    POSTGIS_DEFAULT_HOST,
    POSTGIS_DEFAULT_PORT,
    POSTGIS_DEFAULT_DB,
    POSTGIS_DEFAULT_USER,
    POSTGIS_DEFAULT_PASSWORD,
)
from ..utils.logger import get_logger

logger = get_logger(__name__)


class SyncService:
    """
    Business service untuk sinkronisasi perubahan fitur QGIS ke GeoNode.
    """

    def __init__(self, session_instance=None):
        self._session = session_instance or session
        self._table_columns_cache: Dict[str, Any] = {}

    # ==========================================================
    # Change Detection & Inspection
    # ==========================================================

    def get_existing_table_columns(self, layer: QgsVectorLayer) -> Set[str]:
        """
        Mengambil nama-nama kolom tabel dataset yang ada di basis data GeoNode PostGIS.
        Menggunakan caching singkat (5 detik) untuk performa responsif di antarmuka QGIS.
        """
        if not layer or not layer.isValid():
            return set()

        raw_name = layer.name()
        if ":" in raw_name:
            raw_name = raw_name.split(":")[-1]
        table_name = "".join(c for c in raw_name.lower() if c.isalnum() or c == "_")

        now = datetime.now().timestamp()
        if table_name in self._table_columns_cache:
            cache_time, cached_cols = self._table_columns_cache[table_name]
            if now - cache_time < 5.0:
                return cached_cols

        conn = self._get_postgis_connection()
        if not conn:
            return set()

        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_name = %s",
                (table_name,)
            )
            rows = cur.fetchall()
            if not rows:
                cur.execute(
                    "SELECT table_name FROM information_schema.tables WHERE table_name LIKE %s AND table_schema = 'public'",
                    (f"%{table_name}%",)
                )
                sim = cur.fetchone()
                if sim:
                    table_name = sim[0]
                    cur.execute(
                        "SELECT column_name FROM information_schema.columns WHERE table_name = %s",
                        (table_name,)
                    )
                    rows = cur.fetchall()
            conn.close()
            cols = {r[0].lower() for r in rows}
            self._table_columns_cache[table_name] = (now, cols)
            return cols
        except Exception:
            try:
                conn.close()
            except Exception:
                pass
            return set()

    def get_pending_changes(self, layer: Optional[QgsVectorLayer]) -> Dict[str, Any]:
        """
        Mendeteksi perubahan lokal pada layer QGIS, baik penambahan fitur, perubahan isi atribut/geometri,
        penghapusan fitur, maupun penambahan dan penghapusan field/kolom dataset.
        """
        if not layer or not isinstance(layer, QgsVectorLayer) or not layer.isValid():
            return {
                "is_modified": False,
                "is_editable": False,
                "inserts": 0,
                "updates": 0,
                "deletes": 0,
                "total": 0,
                "added_fields": [],
                "deleted_fields": [],
                "change_log": [],
            }

        is_editable = layer.isEditable()
        is_modified = layer.isModified()
        edit_buffer = layer.editBuffer() if is_editable else None

        now_str = datetime.now().strftime("%d/%m/%Y %H:%M")
        username = self._session.username or "admin"

        change_log: List[Dict[str, str]] = []
        added_field_names: List[str] = []
        deleted_field_names: List[str] = []

        # 1. Periksa penambahan & penghapusan field dari editBuffer aktif
        if edit_buffer:
            added_attrs = edit_buffer.addedAttributes()
            for f in added_attrs:
                fname = f.name()
                if fname not in added_field_names:
                    added_field_names.append(fname)
                    type_str = f.typeName() or str(f.type())
                    change_log.append({
                        "id": fname,
                        "jenis": "Tambah Field",
                        "waktu": now_str,
                        "oleh": username,
                        "details": {
                            "type": "field_add",
                            "field_name": fname,
                            "type_name": type_str,
                            "length": f.length(),
                            "precision": f.precision(),
                            "comment": f.comment(),
                        },
                    })

            deleted_attr_indices = edit_buffer.deletedAttributeIds()
            fields = layer.fields()
            for idx in deleted_attr_indices:
                if 0 <= idx < fields.count():
                    fname = fields.at(idx).name()
                else:
                    fname = f"Field #{idx}"
                if fname not in deleted_field_names:
                    deleted_field_names.append(fname)
                    change_log.append({
                        "id": fname,
                        "jenis": "Hapus Field",
                        "waktu": now_str,
                        "oleh": username,
                        "details": {
                            "type": "field_delete",
                            "field_name": fname,
                            "message": f"Field '{fname}' dihapus dari skema layer.",
                        },
                    })

        # 2. Periksa perbedaan skema dengan basis data PostGIS GeoNode
        # (mendeteksi field baru yang belum ada di PostGIS bahkan jika editBuffer sudah di-commit di QGIS)
        try:
            db_cols = self.get_existing_table_columns(layer)
            if db_cols:
                for f in layer.fields():
                    fname_lower = f.name().lower()
                    if fname_lower not in db_cols and fname_lower not in ("geom", "geometry") and f.name() not in added_field_names:
                        added_field_names.append(f.name())
                        type_str = f.typeName() or str(f.type())
                        change_log.append({
                            "id": f.name(),
                            "jenis": "Tambah Field",
                            "waktu": now_str,
                            "oleh": username,
                            "details": {
                                "type": "field_add",
                                "field_name": f.name(),
                                "type_name": type_str,
                                "length": f.length(),
                                "precision": f.precision(),
                                "comment": f.comment(),
                            },
                        })
        except Exception as e:
            logger.debug(f"Pemeriksaan kolom skema PostGIS: {e}")

        # 3. Fitur Baru Ditambahkan (Insert)
        inserts_count = len(added_field_names)
        if edit_buffer:
            added_features = edit_buffer.addedFeatures()
            inserts_count += len(added_features)
            layer_fields = layer.fields()
            for fid, feat in added_features.items():
                attr_list = []
                for idx in range(layer_fields.count()):
                    fname = layer_fields.at(idx).name()
                    val = feat.attribute(idx)
                    val_str = str(val) if val is not None else "NULL"
                    attr_list.append({
                        "field": fname,
                        "value": val_str,
                    })
                change_log.append({
                    "id": str(fid),
                    "jenis": "Tambah",
                    "waktu": now_str,
                    "oleh": username,
                    "details": {
                        "type": "feature_insert",
                        "fid": fid,
                        "attributes": attr_list,
                        "has_geometry": feat.hasGeometry(),
                    },
                })

        # 4. Fitur Diubah (Update Geometry & Attributes)
        updates_count = 0
        if edit_buffer:
            changed_attrs = edit_buffer.changedAttributeValues()
            changed_geoms = edit_buffer.changedGeometries()
            updated_fids = set(changed_attrs.keys()) | set(changed_geoms.keys())
            updated_fids = updated_fids - set(edit_buffer.addedFeatures().keys())
            updates_count = len(updated_fids)
            layer_fields = layer.fields()

            for fid in sorted(list(updated_fids)):
                attr_diffs = []
                orig_feat = None
                try:
                    req = QgsFeatureRequest().setFilterFid(fid)
                    it = layer.dataProvider().getFeatures(req)
                    orig_feat = next(it, None)
                except Exception:
                    pass

                if fid in changed_attrs:
                    for f_idx, new_val in changed_attrs[fid].items():
                        fname = layer_fields.at(f_idx).name() if 0 <= f_idx < layer_fields.count() else f"Field #{f_idx}"
                        old_val = "-"
                        if orig_feat is not None and 0 <= f_idx < len(orig_feat.attributes()):
                            orig_v = orig_feat.attribute(f_idx)
                            old_val = str(orig_v) if orig_v is not None else "NULL"
                        new_val_str = str(new_val) if new_val is not None else "NULL"
                        attr_diffs.append({
                            "field": fname,
                            "old_value": old_val,
                            "new_value": new_val_str,
                        })

                geom_changed = fid in changed_geoms

                change_log.append({
                    "id": str(fid),
                    "jenis": "Ubah",
                    "waktu": now_str,
                    "oleh": username,
                    "details": {
                        "type": "feature_update",
                        "fid": fid,
                        "attributes": attr_diffs,
                        "geometry_changed": geom_changed,
                    },
                })

        # 5. Fitur Dihapus (Delete)
        deletes_count = len(deleted_field_names)
        if edit_buffer:
            deleted_ids = edit_buffer.deletedFeatureIds()
            deletes_count += len(deleted_ids)
            for fid in sorted(list(deleted_ids)):
                change_log.append({
                    "id": str(fid),
                    "jenis": "Hapus",
                    "waktu": now_str,
                    "oleh": username,
                    "details": {
                        "type": "feature_delete",
                        "fid": fid,
                        "message": f"Fitur dengan ID {fid} dihapus dari layer.",
                    },
                })

        total_changes = inserts_count + updates_count + deletes_count
        effective_modified = is_modified or (len(added_field_names) > 0) or (len(deleted_field_names) > 0)

        return {
            "is_modified": effective_modified,
            "is_editable": is_editable,
            "inserts": inserts_count,
            "updates": updates_count,
            "deletes": deletes_count,
            "total": total_changes,
            "added_fields": added_field_names,
            "deleted_fields": deleted_field_names,
            "change_log": change_log,
        }

    # ==========================================================
    # Synchronization Execution
    # ==========================================================

    def sync_layer(self, layer: Optional[QgsVectorLayer]) -> ServiceResult:
        """
        Mengeksekusi proses sinkronisasi perubahan layer ke GeoNode / GeoServer.
        """
        if not layer or not isinstance(layer, QgsVectorLayer) or not layer.isValid():
            return ServiceResult.fail(message="Layer tidak valid atau belum dipilih.")

        changes = self.get_pending_changes(layer)
        provider_type = layer.providerType().upper()

        logger.info(
            f"Memulai sinkronisasi layer '{layer.name()}' ({provider_type}) | "
            f"Perubahan: {changes['inserts']} tambah, {changes['updates']} ubah, {changes['deletes']} hapus"
        )

        # 1. Pastikan layer memiliki konfigurasi WFS-T yang tepat jika merupakan layer WFS
        if provider_type == "WFS":
            return self._sync_wfs_layer(layer, changes)

        # 2. Jika merupakan layer OGR (Shapefile / GeoJSON)
        return self._sync_ogr_layer(layer, changes)

    def _sync_wfs_layer(self, layer: QgsVectorLayer, changes: Dict[str, Any]) -> ServiceResult:
        """
        Sinkronisasi layer WFS via WFS-T dengan fallback otomatis ke PostGIS database GeoNode.
        """
        # Periksa dan perbarui DataSource jika masih menggunakan version='auto' atau belum memiliki kredensial
        self._ensure_wfs_datasource_compatibility(layer)

        has_schema_changes = bool(changes.get("added_fields")) or (len(changes.get("added_fields", [])) > 0)

        # Jika ada penambahan field baru, WFS Transaction GeoServer tidak mendukung DDL perubahan skema,
        # sehingga perubahan dialihkan langsung ke database PostGIS GeoNode.
        if has_schema_changes:
            logger.info("Terdeteksi penambahan field baru. Menyimpan langsung ke database PostGIS GeoNode...")
            pg_result = self._sync_layer_to_postgis(layer, changes)
            if pg_result.success:
                if layer.isEditable():
                    layer.rollBack()
                layer.dataProvider().reloadData()
                layer.updateFields()
                layer.triggerRepaint()
                return pg_result
            return pg_result

        wfs_t_success = False
        if layer.isEditable() and layer.isModified():
            logger.info("Menyimpan perubahan ke GeoServer via WFS-T commitChanges()...")
            wfs_t_success = layer.commitChanges(stopEditing=False)

            if wfs_t_success:
                layer.triggerRepaint()
                self._reset_and_reload_geoserver()
                raw_name = layer.name().split(":")[-1]
                self._trigger_geonode_updatelayers(raw_name)
                logger.info("Commit WFS-T berhasil disimpan ke GeoServer!")
                return ServiceResult.ok(
                    message=f"Sinkronisasi berhasil! {changes['total']} perubahan tersimpan di GeoNode.",
                    data=changes,
                )
            else:
                errors = layer.commitErrors()
                logger.warning(f"Commit WFS-T langsung ditolak oleh provider/GeoServer ({errors}). Mengalihkan ke sinkronisasi langsung database PostGIS...")

        # Jika WFS-T tidak dapat mengeksekusi, simpan langsung ke backend PostGIS GeoNode!
        pg_result = self._sync_layer_to_postgis(layer, changes)
        if pg_result.success:
            if layer.isEditable():
                layer.rollBack()
            layer.dataProvider().reloadData()
            layer.updateFields()
            layer.triggerRepaint()
            return pg_result

        # Jika keduanya gagal, laporkan error
        errors = layer.commitErrors() if hasattr(layer, "commitErrors") else []
        err_msg = "\n".join(errors) if errors else pg_result.message
        return ServiceResult.fail(message=f"Gagal sinkronisasi WFS:\n{err_msg}")

    def _sync_ogr_layer(self, layer: QgsVectorLayer, changes: Dict[str, Any]) -> ServiceResult:
        """
        Sinkronisasi layer lokal (Shapefile / GeoJSON).
        1. Simpan perubahan ke file lokal (.shp).
        2. Sinkronkan skema (field baru jika ada) dan seluruh data fitur ke database GeoNode (PostGIS).
        3. Segarkan katalog GeoServer & GeoNode agar perubahan langsung muncul di GeoNode.
        """
        if layer.isEditable() and layer.isModified():
            success = layer.commitChanges(stopEditing=False)
            if not success:
                errors = layer.commitErrors()
                return ServiceResult.fail(message=f"Gagal menyimpan perubahan lokal: {errors}")

        layer.triggerRepaint()

        # Eksekusi sinkronisasi data dan skema ke database GeoNode
        return self._sync_layer_to_postgis(layer, changes)

    def _sync_layer_to_postgis(self, layer: QgsVectorLayer, changes: Optional[Dict[str, Any]] = None) -> ServiceResult:
        """
        Menyimpan field baru dan fitur dari layer ke basis data PostGIS GeoNode.
        """
        try:
            import psycopg2
        except ImportError:
            return ServiceResult.fail(
                message="Modul psycopg2 tidak tersedia di environment QGIS untuk sinkronisasi database langsung."
            )

        conn = self._get_postgis_connection()
        if not conn:
            return ServiceResult.fail(
                message="Tidak dapat terhubung ke database PostGIS GeoNode (172.19.0.2 / localhost:5432)."
            )

        # Cari nama tabel yang sesuai di basis data GeoNode
        raw_name = layer.name()
        if ":" in raw_name:
            raw_name = raw_name.split(":")[-1]
        table_name = "".join(c for c in raw_name.lower() if c.isalnum() or c == "_")

        try:
            cur = conn.cursor()

            # 1. Cek apakah tabel ada di PostGIS
            cur.execute(
                "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = %s",
                (table_name,)
            )
            col_rows = cur.fetchall()
            if not col_rows:
                # Coba cari nama tabel yang mirip jika ada prefix/suffix
                cur.execute(
                    "SELECT table_name FROM information_schema.tables WHERE table_name LIKE %s AND table_schema = 'public'",
                    (f"%{table_name}%",)
                )
                similar = cur.fetchone()
                if similar:
                    table_name = similar[0]
                    cur.execute(
                        "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = %s",
                        (table_name,)
                    )
                    col_rows = cur.fetchall()

            if not col_rows:
                conn.close()
                return ServiceResult.fail(
                    message=f"Tabel dataset '{table_name}' tidak ditemukan di database GeoNode."
                )

            existing_cols = {r[0].lower(): r[1] for r in col_rows}
            added_columns = []

            # 2. Deteksi dan tambahkan Field Baru (Kolom Baru) ke skema tabel PostGIS
            for field in layer.fields():
                fname = field.name().lower()
                if fname not in existing_cols and fname not in ("geom", "geometry"):
                    type_name = field.typeName().lower()
                    if "int" in type_name or "long" in type_name:
                        sql_type = "bigint"
                    elif "double" in type_name or "real" in type_name or "float" in type_name:
                        sql_type = "double precision"
                    elif "bool" in type_name:
                        sql_type = "boolean"
                    elif "date" in type_name or "time" in type_name:
                        sql_type = "timestamp without time zone"
                    else:
                        sql_type = "character varying"

                    cur.execute(f"ALTER TABLE {table_name} ADD COLUMN {fname} {sql_type};")
                    added_columns.append(fname)
                    existing_cols[fname] = sql_type
                    logger.info(f"Field baru '{fname}' ({sql_type}) berhasil ditambahkan ke tabel '{table_name}'.")

            conn.commit()

            # 3. Sinkronisasi data fitur ke tabel PostGIS
            cur.execute(
                "SELECT f_geometry_column, srid FROM geometry_columns WHERE f_table_name = %s LIMIT 1",
                (table_name,)
            )
            geom_info = cur.fetchone()
            geom_col = geom_info[0] if geom_info else ("geom" if "geom" in existing_cols else "geometry")
            table_srid = geom_info[1] if (geom_info and geom_info[1]) else 4326

            layer_srid = table_srid
            if hasattr(layer, "crs") and layer.crs().isValid():
                psrid = layer.crs().postgisSrid()
                if psrid and psrid > 0:
                    layer_srid = psrid

            if layer_srid == table_srid:
                geom_sql_expr = f"ST_SetSRID(ST_GeomFromText(%s), {table_srid})"
            else:
                geom_sql_expr = f"ST_Transform(ST_SetSRID(ST_GeomFromText(%s), {layer_srid}), {table_srid})"

            pk_col = "fid" if "fid" in existing_cols else ("id" if "id" in existing_cols else None)
            layer_field_names = [f.name() for f in layer.fields() if f.name().lower() in existing_cols and f.name().lower() != pk_col and f.name().lower() != geom_col]

            updated_count = 0
            inserted_count = 0

            for feat in layer.getFeatures():
                geom = feat.geometry()
                geom_wkt = geom.asWkt() if (geom and not geom.isEmpty()) else None

                # Nilai atribut yang valid untuk tabel
                attr_values = []
                for fname in layer_field_names:
                    val = feat.attribute(fname)
                    # Convert NULL or QVariant invalid
                    if val is None or str(val) == "NULL":
                        attr_values.append(None)
                    else:
                        attr_values.append(val)

                fid_val = feat.attribute(pk_col) if pk_col else None
                row_exists = False
                if fid_val is not None:
                    cur.execute(f"SELECT 1 FROM {table_name} WHERE {pk_col} = %s", (fid_val,))
                    row_exists = cur.fetchone() is not None

                if row_exists and pk_col:
                    # UPDATE baris yang sudah ada
                    set_clauses = [f"{fname} = %s" for fname in layer_field_names]
                    sql_params = list(attr_values)
                    if geom_wkt:
                        set_clauses.append(f"{geom_col} = {geom_sql_expr}")
                        sql_params.append(geom_wkt)
                    sql_params.append(fid_val)

                    update_sql = f"UPDATE {table_name} SET {', '.join(set_clauses)} WHERE {pk_col} = %s"
                    cur.execute(update_sql, sql_params)
                    updated_count += 1
                else:
                    # INSERT fitur baru
                    insert_cols = list(layer_field_names)
                    placeholders = ["%s"] * len(layer_field_names)
                    sql_params = list(attr_values)

                    if geom_wkt:
                        insert_cols.append(geom_col)
                        placeholders.append(geom_sql_expr)
                        sql_params.append(geom_wkt)

                    insert_sql = f"INSERT INTO {table_name} ({', '.join(insert_cols)}) VALUES ({', '.join(placeholders)})"
                    cur.execute(insert_sql, sql_params)
                    inserted_count += 1

            conn.commit()
            conn.close()

            # Bersihkan cache skema kolom lokal agar pembacaan berikutnya akurat
            self._table_columns_cache.clear()

            # 4. Segarkan Katalog GeoServer (Reset + Reload agar schema & field baru langsung dikenali)
            self._reset_and_reload_geoserver()

            # 5. Pemicu pembaruan metadata atribut GeoNode di latar belakang
            self._trigger_geonode_updatelayers(table_name)

            summary_parts = []
            if added_columns:
                summary_parts.append(f"{len(added_columns)} field baru ({', '.join(added_columns)})")
            if updated_count > 0:
                summary_parts.append(f"{updated_count} fitur diperbarui")
            if inserted_count > 0:
                summary_parts.append(f"{inserted_count} fitur baru ditambahkan")

            summary_text = ", ".join(summary_parts) if summary_parts else "data fitur mutakhir"
            msg = f"Sinkronisasi berhasil! {summary_text} telah tersimpan di GeoNode."
            logger.info(msg)

            return ServiceResult.ok(message=msg, data={"added_columns": added_columns, "updated": updated_count, "inserted": inserted_count})

        except Exception as e:
            logger.exception("Gagal sinkronisasi data ke PostGIS GeoNode.")
            if conn:
                try:
                    conn.rollback()
                    conn.close()
                except Exception:
                    pass
            return ServiceResult.fail(message=f"Gagal sinkronisasi ke database GeoNode: {str(e)}")

    def _get_postgis_connection(self):
        """Membuat koneksi ke database PostGIS GeoNode dengan kandidat host otomatis."""
        try:
            import psycopg2
        except ImportError:
            return None

        candidates = [POSTGIS_DEFAULT_HOST, "127.0.0.1", "localhost"]
        try:
            ip = subprocess.check_output(
                ["docker", "inspect", "-f", "{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}", "db4geonode_project"],
                stderr=subprocess.DEVNULL
            ).decode().strip()
            if ip and ip not in candidates:
                candidates.insert(0, ip)
        except Exception:
            pass

        for host in candidates:
            try:
                conn = psycopg2.connect(
                    dbname=POSTGIS_DEFAULT_DB,
                    user=POSTGIS_DEFAULT_USER,
                    password=POSTGIS_DEFAULT_PASSWORD,
                    host=host,
                    port=POSTGIS_DEFAULT_PORT,
                    connect_timeout=2
                )
                return conn
            except Exception:
                continue
        return None

    def _reset_and_reload_geoserver(self) -> bool:
        """
        Mereset store cache dan memuat ulang katalog GeoServer via REST.
        POST /geoserver/rest/reset membersihkan connection cache agar PostGIS column baru seketika terbaca.
        POST /geoserver/rest/reload memuat ulang XML catalog.
        """
        try:
            auth_str = f"{GEOSERVER_ADMIN_USER}:{GEOSERVER_ADMIN_PASSWORD}"
            auth = base64.b64encode(auth_str.encode()).decode()

            # 1. Reset GeoServer Cache
            try:
                req_reset = urllib.request.Request(
                    "http://localhost/geoserver/rest/reset",
                    headers={"Authorization": f"Basic {auth}"},
                    method="POST",
                )
                with urllib.request.urlopen(req_reset, timeout=5) as resp:
                    logger.info(f"GeoServer catalog reset: HTTP {resp.status}")
            except Exception as e_reset:
                logger.warning(f"GeoServer reset warning: {e_reset}")

            # 2. Reload GeoServer Catalog
            req_reload = urllib.request.Request(
                "http://localhost/geoserver/rest/reload",
                headers={"Authorization": f"Basic {auth}"},
                method="POST",
            )
            with urllib.request.urlopen(req_reload, timeout=5) as resp:
                logger.info(f"GeoServer catalog reload: HTTP {resp.status}")
                return resp.status == 200
        except Exception as e:
            logger.warning(f"Gagal reset/reload GeoServer: {e}")
            return False

    def _reload_geoserver_catalog(self) -> bool:
        return self._reset_and_reload_geoserver()

    def _trigger_geonode_updatelayers(self, table_name: str) -> None:
        """Memicu pembaruan atribut layer GeoNode di latar belakang tanpa menghambat UI."""
        try:
            subprocess.Popen(
                ["docker", "exec", "-i", "django4geonode_project", "python", "manage.py", "updatelayers", f"--filter={table_name}"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            logger.info(f"Triggered GeoNode updatelayers for {table_name}")
        except Exception as e:
            logger.warning(f"Tidak dapat memicu updatelayers: {e}")

    # ==========================================================
    # Revert Changes
    # ==========================================================

    def revert_changes(self, layer: Optional[QgsVectorLayer]) -> ServiceResult:
        """
        Membatalkan seluruh perubahan lokal yang belum dikomit (rollback).
        """
        if not layer or not isinstance(layer, QgsVectorLayer) or not layer.isValid():
            return ServiceResult.fail(message="Layer tidak valid.")

        if layer.isEditable():
            logger.info(f"Membatalkan perubahan pada layer '{layer.name()}'...")
            layer.rollBack()
            layer.triggerRepaint()
            return ServiceResult.ok(message=f"Seluruh perubahan pada layer '{layer.name()}' telah dibatalkan.")

        return ServiceResult.ok(message="Tidak ada perubahan yang perlu dibatalkan.")

    # ==========================================================
    # Helper: Compatibility Fixer
    # ==========================================================

    def _ensure_wfs_datasource_compatibility(self, layer: QgsVectorLayer) -> None:
        """
        Memastikan URI WFS layer menggunakan version='1.0.0', memiliki kredensial GeoServer yang tepat,
        dan tidak terkendala axis order atau mode read-only.
        """
        src = layer.source()
        need_update = False

        if "version='auto'" in src or "version='2.0.0'" in src or "version='1.1.0'" in src:
            src = src.replace("version='auto'", "version='1.0.0'")
            src = src.replace("version='2.0.0'", "version='1.0.0'")
            src = src.replace("version='1.1.0'", "version='1.0.0'")
            need_update = True
        elif "version=" not in src:
            src += " version='1.0.0'"
            need_update = True

        # Periksa dan perbaiki kredensial GeoServer
        if "localhost" in src or "127.0.0.1" in src:
            if f"password='{GEOSERVER_ADMIN_PASSWORD}'" not in src:
                if "username=" in src:
                    src = re.sub(r"username='[^']*'", f"username='{GEOSERVER_ADMIN_USER}'", src)
                    src = re.sub(r"password='[^']*'", f"password='{GEOSERVER_ADMIN_PASSWORD}'", src)
                else:
                    src += f" username='{GEOSERVER_ADMIN_USER}' password='{GEOSERVER_ADMIN_PASSWORD}'"
                need_update = True
        elif "username=" not in src:
            user = self._session.username or GEOSERVER_ADMIN_USER
            pwd = getattr(self._session.data, "password", "") or GEOSERVER_ADMIN_PASSWORD
            if user and pwd:
                src += f" username='{user}' password='{pwd}'"
                need_update = True

        if need_update:
            logger.info(f"Memperbarui DataSource WFS untuk kompatibilitas WFS-T: {layer.name()}")
            layer.setDataSource(src, layer.name(), "WFS")

        # Pastikan layer tidak dalam status read-only agar tombol toggle editing aktif
        layer.setReadOnly(False)


sync_service = SyncService()

