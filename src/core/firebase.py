import logging

import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.client import Client

logger = logging.getLogger(__name__)


def initialize_firebase() -> Client:
    if firebase_admin._apps:
        return firestore.client()

    cred = credentials.Certificate("firebase-credentials.json")
    firebase_admin.initialize_app(cred)
    logger.info("Firebase initialized")
    return firestore.client()
