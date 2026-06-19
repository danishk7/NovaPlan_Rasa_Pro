from typing import Any


def user_public(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "userId": row["user_id"],
        "name": row.get("name"),
        "email": row.get("email"),
        "role": row.get("role", "user"),
        "bio": row.get("bio"),
        "location": row.get("location"),
        "loyaltyTier": row.get("loyalty_tier", "Basic"),
    }


def session_public(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "sesId": row["ses_id"],
        "userId": row.get("user_id"),
        "userName": row.get("user_name"),
        "status": row.get("status"),
        "lastMessage": row.get("last_message"),
        "updatedAt": row.get("updated_at"),
        "needsHuman": "true" if row.get("needs_human") else "false",
    }


def conversation_public(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "covId": row["cov_id"],
        "sesId": row.get("ses_id"),
        "userId": row.get("user_id"),
        "userName": row.get("user_name"),
        "userRole": row.get("user_role"),
        "text": row.get("text"),
        "timestamp": row.get("timestamp"),
    }


def itinerary_public(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "itnId": row["itn_id"],
        "userId": row.get("user_id"),
        "time": row.get("time"),
        "title": row.get("title"),
        "summary": row.get("summary") or {},
        "status": row.get("status"),
        "createdAt": row.get("created_at"),
    }


def contact_public(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "conId": row["con_id"],
        "name": row["name"],
        "email": row["email"],
        "topic": row["topic"],
        "message": row["message"],
        "createdAt": row["created_at"],
    }
