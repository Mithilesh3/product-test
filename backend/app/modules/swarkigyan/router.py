from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.db.models import User
from app.modules.swarkigyan.schemas import SwarChatRequest, SwarChatResponse
from app.modules.swarkigyan.service import (
    contains_abusive_language,
    detect_language,
    generate_swarkigyan_reply,
)
from app.modules.users.router import get_current_user

router = APIRouter(tags=["Swarkigyan"])


def _warning_text(language: str, count: int) -> str:
    if language == "hindi":
        return (
            f"कृपया अपशब्द का उपयोग बंद करें। यह आपकी चेतावनी {count}/3 है। "
            "अगली गलती पर खाता ब्लॉक हो जाएगा।"
        )
    if language == "hinglish":
        return (
            f"Kripya abusive words use na karein. Yeh warning {count}/3 hai. "
            "Agli baar account block ho jayega."
        )
    return (
        f"Please stop using abusive words. This is warning {count}/3. "
        "Next violation will block your account."
    )


@router.post("/chat", response_model=SwarChatResponse)
def swar_chat(
    payload: SwarChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    language = detect_language(payload.message, payload.language_preference)

    if contains_abusive_language(payload.message):
        current_user.abuse_warnings = int(current_user.abuse_warnings or 0) + 1

        if current_user.abuse_warnings >= 3:
            current_user.is_blocked = True
            db.commit()
            raise HTTPException(
                status_code=401,
                detail="Account blocked after repeated abusive messages",
            )

        db.commit()
        return SwarChatResponse(
            reply=_warning_text(language, int(current_user.abuse_warnings)),
            language=language,
            safe_guard_applied=True,
            warning_count=int(current_user.abuse_warnings),
            account_blocked=False,
        )

    reply, language, safe_guard_applied = generate_swarkigyan_reply(payload)
    return SwarChatResponse(
        reply=reply,
        language=language,
        safe_guard_applied=safe_guard_applied,
        warning_count=int(current_user.abuse_warnings or 0),
        account_blocked=False,
    )
