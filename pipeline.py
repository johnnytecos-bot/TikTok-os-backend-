"""
pipeline.py
The orchestrator. Run this file once a day (manually, cron, or a scheduled
task) to generate one new, guaranteed-unique quote card and send it to
TikTok drafts.

Flow:
  1. Ask Groq for a quote + hashtags.
  2. Check history — if it's a duplicate/near-duplicate, ask Groq again.
  3. Pick the next template in rotation (never repeats the last style).
  4. Render the card image locally.
  5. Upload it to TikTok as a draft.
  6. Record it in history so it's never generated again.
"""

import sys
from pathlib import Path
from datetime import datetime, timezone

from config import OUTPUT_DIR, MAX_GENERATION_RETRIES
from groq_client import generate_quote, GroqGenerationError
from history_store import is_duplicate, last_template_id, record_post, history_count
from templates import pick_next_template
from card_renderer import render_card
from tiktok_client import save_photo_to_drafts, TikTokUploadError
from supabase_client import upload_card, SupabaseUploadError


def get_unique_quote() -> dict:
    """Keeps asking Groq for a quote until we get one that isn't a duplicate."""
    seen_this_run = []

    for attempt in range(1, MAX_GENERATION_RETRIES + 1):
        try:
            result = generate_quote(avoid_quotes=seen_this_run)
        except GroqGenerationError as exc:
            print(f"[attempt {attempt}] Groq generation failed: {exc}")
            continue

        seen_this_run.append(result["quote"])

        if is_duplicate(result["quote"]):
            print(f"[attempt {attempt}] Duplicate/near-duplicate, retrying: {result['quote']!r}")
            continue

        return result

    raise RuntimeError(
        f"Could not get a unique quote after {MAX_GENERATION_RETRIES} attempts."
    )


def _default_image_hosting_fn(local_path: Path) -> str:
    """Uploads to Supabase Storage and returns the public URL. Used unless
    a different image_hosting_fn is passed into run()."""
    remote_filename = local_path.name  # e.g. card_20260901_090000.png
    return upload_card(local_path, remote_filename)


def run(image_hosting_fn=None, publish_to_tiktok: bool = True) -> dict:
    """
    Runs one full pipeline pass.

    image_hosting_fn: optional callable that takes a local file path and
    returns a public HTTPS URL for it. Defaults to uploading to Supabase
    Storage. Required (in some form) if publish_to_tiktok=True, since
    TikTok needs a reachable URL, not a local file path.
    """
    if image_hosting_fn is None:
        image_hosting_fn = _default_image_hosting_fn
    print(f"--- Run started {datetime.now(timezone.utc).isoformat()} (history: {history_count()} posts) ---")

    quote_data = get_unique_quote()
    quote, hashtags = quote_data["quote"], quote_data["hashtags"]
    print(f"Quote: {quote}")
    print(f"Hashtags: {hashtags}")

    template_id = pick_next_template(last_template_id())
    print(f"Template: {template_id}")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output_path = OUTPUT_DIR / f"card_{timestamp}.png"
    render_card(quote, template_id, output_path)
    print(f"Rendered card: {output_path}")

    tiktok_response = None
    if publish_to_tiktok:
        try:
            image_url = image_hosting_fn(output_path)
        except SupabaseUploadError as exc:
            print(f"Supabase upload failed: {exc}")
            print("Card was still rendered and saved locally — nothing lost.")
            record_post(quote, hashtags, template_id)
            return {
                "quote": quote, "hashtags": hashtags, "template_id": template_id,
                "image_path": str(output_path), "tiktok_response": None, "error": str(exc),
            }
        print(f"Hosted at: {image_url}")

        try:
            tiktok_response = save_photo_to_drafts(image_url, title="", hashtags=hashtags)
            print(f"Sent to TikTok drafts: {tiktok_response}")
        except TikTokUploadError as exc:
            print(f"TikTok upload failed: {exc}")
            print("Card was still rendered and saved locally — nothing lost.")
            record_post(quote, hashtags, template_id)
            return {
                "quote": quote, "hashtags": hashtags, "template_id": template_id,
                "image_path": str(output_path), "tiktok_response": None, "error": str(exc),
            }

    # Only record to history once everything succeeded (or TikTok step was skipped on purpose)
    record_post(quote, hashtags, template_id)

    return {
        "quote": quote,
        "hashtags": hashtags,
        "template_id": template_id,
        "image_path": str(output_path),
        "tiktok_response": tiktok_response,
    }


if __name__ == "__main__":
    import os

    # PUBLISH_TO_TIKTOK env var controls whether this run actually uploads
    # to Supabase + sends to TikTok, or just renders the card locally.
    # Defaults to "false" so a bare local run is always safe to try.
    # Render's cron job sets this to "true" once your keys are configured.
    should_publish = os.environ.get("PUBLISH_TO_TIKTOK", "false").lower() == "true"
    result = run(publish_to_tiktok=should_publish)
    print("\nDone:", result)
