COMMENT_BODY_MAX_LENGTH = 2000

INVALID_MENTIONS_ERROR_DETAIL = "Une ou plusieurs mentions sont invalides."
INVALID_PARENT_COMMENT_ERROR_DETAIL = "Le commentaire parent est invalide."
CANNOT_REPLY_TO_SIGNAL_COMMENT_ERROR_DETAIL = (
    "Impossible de répondre à un commentaire Signal depuis une Action."
)
CANNOT_REPLY_TO_SIGNAL_COMMENT_FROM_EXECUTION_ERROR_DETAIL = (
    "Impossible de répondre à un commentaire Signal depuis un Plan d'action."
)
CANNOT_REPLY_TO_REPLY_ERROR_DETAIL = "Impossible de répondre à une réponse."
NOT_ACTION_ROOT_COMMENT_ERROR_DETAIL = "Seul un commentaire racine Action peut être ciblé."
NOT_EXECUTION_ROOT_COMMENT_ERROR_DETAIL = (
    "Seul un commentaire racine Plan d'action peut être ciblé."
)
ALREADY_RESOLVED_ERROR_DETAIL = "Ce commentaire est déjà résolu."
NOT_RESOLVED_ERROR_DETAIL = "Ce commentaire n'est pas résolu."
SIGNAL_COMMENT_PARENT_NOT_ALLOWED_ERROR_DETAIL = (
    "Les réponses ne sont pas disponibles sur les commentaires Signal."
)

ACTION_PLAN_COMMENT_ATTACHMENT_MAX_BYTES = 10 * 1024 * 1024
ACTION_PLAN_COMMENT_ATTACHMENTS_MAX_PER_COMMENT = 4
ACTION_PLAN_COMMENT_UPLOAD_TTL_HOURS = 24
ACTION_PLAN_COMMENT_RETENTION_DAYS = 30
ACTION_PLAN_COMMENT_PURGE_BATCH_SIZE = 1000

ATTACHMENTS_NOT_ALLOWED_ERROR_DETAIL = (
    "Les pièces jointes ne peuvent être ajoutées que lorsque le plan est "
    "en cours ou en attente de validation."
)
ATTACHMENT_INVALID_ERROR_DETAIL = "Une ou plusieurs pièces jointes sont invalides."
ATTACHMENT_NOT_OWNED_ERROR_DETAIL = "Cette pièce jointe n'appartient pas à l'auteur."
ATTACHMENT_WRONG_EXECUTION_ERROR_DETAIL = (
    "Cette pièce jointe n'appartient pas à ce plan d'action."
)
ATTACHMENT_ALREADY_USED_ERROR_DETAIL = "Cette pièce jointe a déjà été utilisée."
ATTACHMENT_NOT_READY_ERROR_DETAIL = "Cette pièce jointe n'est pas prête."
ATTACHMENT_EXPIRED_ERROR_DETAIL = "La réservation de cette pièce jointe a expiré."
ATTACHMENT_TOO_LARGE_ERROR_DETAIL = "Le fichier dépasse la taille maximale de 10 Mo."
ATTACHMENT_UNSUPPORTED_TYPE_ERROR_DETAIL = "Ce type de fichier n'est pas supporté."
ATTACHMENT_INVALID_CONTENT_ERROR_DETAIL = "Le contenu du fichier est invalide."
ATTACHMENT_MISSING_OBJECT_ERROR_DETAIL = "Le fichier téléversé est introuvable."
ATTACHMENT_MAX_COUNT_ERROR_DETAIL = (
    f"Un commentaire accepte au plus {ACTION_PLAN_COMMENT_ATTACHMENTS_MAX_PER_COMMENT} "
    "pièces jointes."
)
