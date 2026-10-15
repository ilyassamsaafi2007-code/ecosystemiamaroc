"""
store.py — stockage des données de l'application (comptes, commentaires, candidatures, photos d'identité).

Deux implémentations, même interface :
  * LocalStore    : fichiers JSON + dossier de photos. Pour le développement et les hébergements
                    avec disque permanent (VPS, PythonAnywhere...). C'est le mode par défaut.
  * SupabaseStore : base Postgres + stockage privé de Supabase, via leur API REST. Obligatoire sur
                    Vercel (système de fichiers en lecture seule, rien n'est conservé entre deux requêtes).

Le choix est automatique : si SUPABASE_URL et SUPABASE_SERVICE_KEY sont définis -> Supabase.
"""

import json
import os
from pathlib import Path

import requests

KYC_KINDS = ("cin_recto", "cin_verso", "selfie")


# ====================================================================== local ====

class LocalStore:
    def __init__(self, base):
        self.base = Path(base)
        self.users_f = self.base / "users.json"
        self.comments_f = self.base / "commentaires.json"
        self.cands_f = self.base / "candidatures.json"
        self.kyc_dir = self.base / "kyc"

    # -- helpers
    def _read(self, path):
        try:
            return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def _write(self, path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    # -- utilisateurs
    def user_get(self, email):
        return self._read(self.users_f).get(email)

    def user_put(self, email, user):
        users = self._read(self.users_f)
        users[email] = user
        self._write(self.users_f, users)

    def users_all(self):
        return self._read(self.users_f)

    # -- commentaires : {lien_offre: [commentaire, ...]}
    def comments_all(self):
        return self._read(self.comments_f)

    def comment_add(self, lien, comment):
        data = self._read(self.comments_f)
        data.setdefault(lien, []).append(comment)
        self._write(self.comments_f, data)

    def comment_delete(self, cid):
        data = self._read(self.comments_f)
        for liste in data.values():
            for c in liste:
                if c.get("id") == cid:
                    liste.remove(c)
                    self._write(self.comments_f, data)
                    return True
        return False

    # -- candidatures : {email: {cle: True}}
    def cands_get(self, email):
        return dict(self._read(self.cands_f).get(email, {})) if email else {}

    def cand_toggle(self, email, cle):
        data = self._read(self.cands_f)
        mine = data.setdefault(email, {})
        if mine.get(cle):
            mine.pop(cle)
        else:
            mine[cle] = True
        self._write(self.cands_f, data)

    # -- photos d'identité
    def kyc_put(self, uid, kind, data):
        d = self.kyc_dir / uid
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{kind}.jpg").write_bytes(data)

    def kyc_get(self, uid, kind):
        p = self.kyc_dir / uid / f"{kind}.jpg"
        return p.read_bytes() if p.is_file() else None

    def kyc_delete(self, uid):
        d = self.kyc_dir / uid
        if d.is_dir():
            for f in d.glob("*.jpg"):
                f.unlink(missing_ok=True)
            try:
                d.rmdir()
            except OSError:
                pass


# =================================================================== supabase ====

class SupabaseStore:
    """Tables attendues : app_users, app_comments, app_candidatures (voir supabase_schema.sql)
    et un bucket PRIVÉ nommé 'kyc'. La clé service_role reste côté serveur (variable d'environnement)."""

    def __init__(self, url, service_key, bucket="kyc"):
        self.url = url.rstrip("/")
        self.bucket = bucket
        # Nouvelles clés (sb_secret_...) : uniquement dans l'en-tête apikey (ce ne sont pas des JWT).
        # Ancienne clé service_role (JWT) : apikey + Authorization.
        self.auth = {"apikey": service_key}
        if not service_key.startswith("sb_"):
            self.auth["Authorization"] = f"Bearer {service_key}"
        self.http = requests.Session()

    # -- REST (PostgREST)
    def _rest(self, method, table, params=None, body=None, prefer=None):
        headers = {**self.auth, "Content-Type": "application/json"}
        if prefer:
            headers["Prefer"] = prefer
        r = self.http.request(method, f"{self.url}/rest/v1/{table}", params=params,
                              json=body, headers=headers, timeout=15)
        r.raise_for_status()
        return r

    # -- utilisateurs
    def user_get(self, email):
        rows = self._rest("GET", "app_users", {"email": f"eq.{email}", "select": "data"}).json()
        return rows[0]["data"] if rows else None

    def user_put(self, email, user):
        self._rest("POST", "app_users", {"on_conflict": "email"}, {"email": email, "data": user},
                   prefer="resolution=merge-duplicates,return=minimal")

    def users_all(self):
        rows = self._rest("GET", "app_users", {"select": "email,data", "limit": "10000"}).json()
        return {r["email"]: r["data"] for r in rows}

    # -- commentaires
    def comments_all(self):
        rows = self._rest("GET", "app_comments", {"select": "lien,data", "limit": "10000"}).json()
        out = {}
        for r in rows:
            out.setdefault(r["lien"], []).append(r["data"])
        return out

    def comment_add(self, lien, comment):
        self._rest("POST", "app_comments", body={"id": comment["id"], "lien": lien, "data": comment},
                   prefer="return=minimal")

    def comment_delete(self, cid):
        r = self._rest("DELETE", "app_comments", {"id": f"eq.{cid}"}, prefer="return=representation")
        return bool(r.json())

    # -- candidatures
    def cands_get(self, email):
        if not email:
            return {}
        rows = self._rest("GET", "app_candidatures", {"email": f"eq.{email}", "select": "cle"}).json()
        return {r["cle"]: True for r in rows}

    def cand_toggle(self, email, cle):
        flt = {"email": f"eq.{email}", "cle": f"eq.{cle}"}
        if self._rest("GET", "app_candidatures", {**flt, "select": "cle"}).json():
            self._rest("DELETE", "app_candidatures", flt, prefer="return=minimal")
        else:
            self._rest("POST", "app_candidatures", body={"email": email, "cle": cle},
                       prefer="resolution=merge-duplicates,return=minimal")

    # -- photos d'identité (bucket privé)
    def _obj(self, uid, kind):
        return f"{self.url}/storage/v1/object/{self.bucket}/{uid}/{kind}.jpg"

    def kyc_put(self, uid, kind, data):
        r = self.http.post(self._obj(uid, kind), data=data, timeout=30,
                           headers={**self.auth, "Content-Type": "image/jpeg", "x-upsert": "true"})
        r.raise_for_status()

    def kyc_get(self, uid, kind):
        r = self.http.get(self._obj(uid, kind), headers=self.auth, timeout=30)
        if r.status_code in (400, 404):      # "Object not found"
            return None
        r.raise_for_status()
        return r.content

    def kyc_delete(self, uid):
        r = self.http.delete(f"{self.url}/storage/v1/object/{self.bucket}", headers=self.auth, timeout=30,
                             json={"prefixes": [f"{uid}/{k}.jpg" for k in KYC_KINDS]})
        r.raise_for_status()


def make_store(data_dir):
    url, key = os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_SERVICE_KEY")
    if url and key:
        return SupabaseStore(url, key, os.environ.get("SUPABASE_BUCKET", "kyc"))
    return LocalStore(data_dir)
