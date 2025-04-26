from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update as sqlalchemy_update
import uuid

from .database import User 
from .auth_models import UserCreate

async def get_user_by_firebase_uid(db: AsyncSession, firebase_uid: str) -> User | None:
    """Fetches a user by their Firebase UID."""
    result = await db.execute(select(User).filter(User.firebase_uid == firebase_uid))
    return result.scalars().first()

async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    """Fetches a user by their email."""
    result = await db.execute(select(User).filter(User.email == email))
    return result.scalars().first()

async def get_user_by_id(db: AsyncSession, user_id: str) -> User | None:
    """Fetches a user by their internal ID."""
    result = await db.execute(select(User).filter(User.id == user_id))
    return result.scalars().first()


async def create_db_user(db: AsyncSession, user_data: UserCreate) -> User:
    """Creates a new user in the database."""
    internal_id = str(uuid.uuid4())
    db_user = User(
        id=internal_id,
        firebase_uid=user_data.firebase_uid,
        email=user_data.email,
        name=user_data.name,
        picture=str(user_data.picture) if user_data.picture else None
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

async def update_db_user(db: AsyncSession, db_user: User, updates: dict) -> User:
     """Updates user information."""
     await db.execute(
         sqlalchemy_update(User)
         .where(User.id == db_user.id)
         .values(**updates)
     )
     await db.commit()
     await db.refresh(db_user) # Refresh to get updated values
     return db_user

async def get_or_create_db_user(db: AsyncSession, decoded_token: dict) -> User:
    """
    Finds a user by Firebase UID or Email, or creates a new one.
    Updates existing user's name/picture if changed.
    """
    firebase_uid = decoded_token.get("uid")
    email = decoded_token.get("email")
    name = decoded_token.get("name")
    picture = decoded_token.get("picture")

    if not firebase_uid or not email:
        raise ValueError("Firebase token missing required claims (UID or email).")

    db_user = await get_user_by_firebase_uid(db, firebase_uid=firebase_uid)

    if db_user:
        print(f"CRUD: Found user by Firebase UID: {db_user.id}")
        updates_needed = {}
        if db_user.name != name:
            updates_needed['name'] = name
        if db_user.picture != picture:
            updates_needed['picture'] = str(picture) if picture else None

        if updates_needed:
             print(f"CRUD: Updating user {db_user.id} with: {updates_needed}")
             db_user = await update_db_user(db, db_user, updates_needed)

        return db_user
    else:
        db_user_by_email = await get_user_by_email(db, email=email)
        if db_user_by_email:
             print(f"CRUD: Found user by email {email}, linking Firebase UID {firebase_uid}")
             updates_needed = {'firebase_uid': firebase_uid}
             if db_user_by_email.name != name: updates_needed['name'] = name
             if db_user_by_email.picture != picture: updates_needed['picture'] = str(picture) if picture else None

             db_user = await update_db_user(db, db_user_by_email, updates_needed)
             return db_user
        else:
             print(f"CRUD: Creating new user for Firebase UID: {firebase_uid}")
             user_create_data = UserCreate(
                 firebase_uid=firebase_uid,
                 email=email,
                 name=name,
                 picture=picture
             )
             new_user = await create_db_user(db, user_data=user_create_data)
             return new_user