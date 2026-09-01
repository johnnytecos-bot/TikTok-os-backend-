"""
supabase_client.py
Uploads a finished card PNG to a Supabase Storage bucket and returns the
public URL — this is what gets passed to tiktok_client.py, since TikTok's
API needs a public HTTPS link, not a local file.

Setup (one-time, in your Supabase project dashboard):
  1. Storage -> Create bucket -> name it "media" -> set it Public.
  2. Project Settings -> API -> copy your Project URL and service_role key
     (or anon key, if the bucket's public policy allows anon uploads).
"""

from pathlib import Path

import requests

from config import SUPABASE_URL, SUPABASE_KEY, SUPABASE_BUCKET


class SupabaseUploadError(Exception):
    pass


def upload_card(local_path: Path, remote_filename: str) -> str:
    """
    Uploads the file at local_path to the Supabase bucket under
    remote_filename, and returns its public URL.
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise SupabaseUploadError("SUPABASE_URL / SUPABASE_KEY not set in the environment.")

    upload_url = f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_BUCKET}/{remote_filename}"

    with open(local_path, "rb") as f:
        response = requests.post(
            upload_url,
            headers={
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "apikey": SUPABASE_KEY,
                "Content-Type": "image/png",
                # x-upsert=true lets a re-run overwrite a same-named file instead of erroring
                "x-upsert": "true",
            },
            data=f,
            timeout=30,
        )

    if response.status_code not in (200, 201):
        raise SupabaseUploadError(f"Supabase upload failed ({response.status_code}): {response.text}")

    public_url = f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_BUCKET}/{remote_filename}"
    return public_url
