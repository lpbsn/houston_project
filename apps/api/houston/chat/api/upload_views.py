from __future__ import annotations

import uuid

from django.conf import settings
from django.http import FileResponse, Http404, HttpResponseRedirect
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from houston.accounts.api.serializers import ApiErrorResponseSerializer
from houston.accounts.authentication import BearerAccessTokenAuthentication
from houston.chat.api.serializers import (
    ChatReserveUploadRequestSerializer,
    ChatReserveUploadResponseSerializer,
    ChatSharedMediaResponseSerializer,
    ChatUploadCompleteResponseSerializer,
    serialize_attachment,
)
from houston.chat.api.views import (
    CanAccessChat,
    ChatRateLimitedMixin,
    EstablishmentScopedChatMixin,
    _chat_error_response,
    _resolve_membership,
)
from houston.chat.constants import CHAT_GALLERY_PAGE_SIZE
from houston.chat.exceptions import ChatError, ChatValidationError
from houston.chat.models import ChatMessageAttachment, ChatUpload
from houston.chat.selectors import get_conversation_for_participant
from houston.chat.upload_services import (
    build_chat_upload_put_url,
    complete_chat_upload,
    generate_chat_attachment_presigned_get,
    get_reserved_chat_upload,
    reserve_chat_upload,
    store_chat_upload_content,
)
from houston.establishments.permissions import HasActiveMembership
from houston.uploads.private_storage import (
    PRIVATE_MEDIA_BACKEND_S3,
    get_chat_private_media_storage,
)
from rest_framework import permissions, status
from rest_framework.parsers import BaseParser
from rest_framework.response import Response
from rest_framework.views import APIView


class _RawBodyParser(BaseParser):
    media_type = "*/*"

    def parse(self, stream, media_type=None, parser_context=None):
        return stream.read()


def _is_s3() -> bool:
    backend = getattr(settings, "HOUSTON_PRIVATE_MEDIA_BACKEND", "")
    return (backend or "").strip().lower() == PRIVATE_MEDIA_BACKEND_S3


class ChatReserveUploadView(ChatRateLimitedMixin, EstablishmentScopedChatMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [
        permissions.IsAuthenticated,
        HasActiveMembership,
        CanAccessChat,
    ]
    throttle_scope = settings.CHAT_THROTTLE_SCOPE_WS_TICKET

    @extend_schema(
        tags=["chat"],
        request=ChatReserveUploadRequestSerializer,
        responses={
            201: ChatReserveUploadResponseSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def post(self, request, establishment_id):
        membership = _resolve_membership(request, self.establishment_id)
        if isinstance(membership, Response):
            return membership
        body = ChatReserveUploadRequestSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        try:
            upload = reserve_chat_upload(
                actor_membership=membership,
                conversation_id=body.validated_data["conversation_id"],
                original_filename=body.validated_data["filename"],
                content_type=body.validated_data["content_type"],
                size_bytes=body.validated_data["size_bytes"],
            )
        except ChatError as exc:
            return _chat_error_response(exc)
        return Response(
            ChatReserveUploadResponseSerializer(
                {
                    "upload_id": upload.id,
                    "put_url": build_chat_upload_put_url(upload=upload, request=request),
                    "expires_at": upload.expires_at,
                }
            ).data,
            status=status.HTTP_201_CREATED,
        )


class ChatUploadContentView(EstablishmentScopedChatMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [
        permissions.IsAuthenticated,
        HasActiveMembership,
        CanAccessChat,
    ]
    parser_classes = [_RawBodyParser]

    @extend_schema(
        tags=["chat"],
        request=None,
        responses={
            204: OpenApiResponse(description="Content stored."),
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def put(self, request, establishment_id, upload_id):
        if _is_s3():
            return Response(
                {"code": "validation_error", "detail": "Use the presigned PUT URL."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        membership = _resolve_membership(request, self.establishment_id)
        if isinstance(membership, Response):
            return membership
        upload = ChatUpload.objects.filter(
            id=upload_id,
            establishment_id=self.establishment_id,
            uploaded_by_membership_id=membership.id,
        ).first()
        if upload is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        payload = request.data if isinstance(request.data, (bytes, bytearray)) else request.body
        try:
            store_chat_upload_content(upload=upload, payload=bytes(payload))
        except ChatError as exc:
            return _chat_error_response(exc)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ChatRefreshUploadPresignView(EstablishmentScopedChatMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [
        permissions.IsAuthenticated,
        HasActiveMembership,
        CanAccessChat,
    ]

    @extend_schema(
        tags=["chat"],
        request=None,
        responses={
            200: ChatReserveUploadResponseSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=ApiErrorResponseSerializer),
            403: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def post(self, request, establishment_id, upload_id):
        membership = _resolve_membership(request, self.establishment_id)
        if isinstance(membership, Response):
            return membership
        try:
            upload = get_reserved_chat_upload(
                actor_membership=membership,
                upload_id=uuid.UUID(str(upload_id)),
            )
        except ChatError as exc:
            return _chat_error_response(exc)
        return Response(
            ChatReserveUploadResponseSerializer(
                {
                    "upload_id": upload.id,
                    "put_url": build_chat_upload_put_url(upload=upload, request=request),
                    "expires_at": upload.expires_at,
                }
            ).data
        )


class ChatCompleteUploadView(EstablishmentScopedChatMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [
        permissions.IsAuthenticated,
        HasActiveMembership,
        CanAccessChat,
    ]

    @extend_schema(
        tags=["chat"],
        request=None,
        responses={
            200: ChatUploadCompleteResponseSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def post(self, request, establishment_id, upload_id):
        membership = _resolve_membership(request, self.establishment_id)
        if isinstance(membership, Response):
            return membership
        try:
            upload = complete_chat_upload(
                actor_membership=membership,
                upload_id=uuid.UUID(str(upload_id)),
            )
        except ChatError as exc:
            return _chat_error_response(exc)
        return Response(
            ChatUploadCompleteResponseSerializer(
                {
                    "upload_id": upload.id,
                    "status": upload.status,
                    "kind": upload.kind,
                    "content_type": upload.content_type,
                    "size_bytes": upload.size_bytes,
                }
            ).data
        )


class ChatAttachmentPreviewView(EstablishmentScopedChatMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [
        permissions.IsAuthenticated,
        HasActiveMembership,
        CanAccessChat,
    ]

    @extend_schema(
        tags=["chat"],
        parameters=[
            OpenApiParameter(
                name="variant",
                required=False,
                type=str,
                enum=["full", "thumbnail"],
            )
        ],
        responses={
            200: OpenApiResponse(description="Binary attachment."),
            302: OpenApiResponse(description="Redirect to presigned GET."),
            404: OpenApiResponse(description="Not found."),
        },
    )
    def get(self, request, establishment_id, attachment_id):
        membership = _resolve_membership(request, self.establishment_id)
        if isinstance(membership, Response):
            return membership
        attachment = (
            ChatMessageAttachment.objects.select_related(
                "upload",
                "message__conversation",
            )
            .filter(id=attachment_id, upload__establishment_id=self.establishment_id)
            .first()
        )
        if attachment is None:
            raise Http404
        conversation = get_conversation_for_participant(
            establishment_id=self.establishment_id,
            conversation_id=attachment.message.conversation_id,
            membership_id=membership.id,
        )
        if conversation is None:
            raise Http404
        variant = request.query_params.get("variant") or "full"
        if variant == "thumbnail":
            storage_key = attachment.upload.thumbnail_storage_key
            content_type = "image/jpeg"
        else:
            storage_key = attachment.upload.storage_key
            content_type = attachment.content_type
        if not storage_key:
            raise Http404
        if _is_s3():
            url = generate_chat_attachment_presigned_get(storage_key=storage_key)
            response = HttpResponseRedirect(url)
            response["Referrer-Policy"] = "no-referrer"
            response["Cache-Control"] = "private, max-age=60, must-revalidate"
            return response
        storage = get_chat_private_media_storage()
        if not storage.exists(storage_key):
            raise Http404
        handle = storage.open(storage_key, "rb")
        response = FileResponse(handle, content_type=content_type)
        response["Referrer-Policy"] = "no-referrer"
        response["Cache-Control"] = "private, max-age=60, must-revalidate"
        return response


class ChatSharedMediaView(EstablishmentScopedChatMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [
        permissions.IsAuthenticated,
        HasActiveMembership,
        CanAccessChat,
    ]

    @extend_schema(
        tags=["chat"],
        parameters=[
            OpenApiParameter(name="kind", required=False, type=str),
            OpenApiParameter(name="cursor", required=False, type=str),
        ],
        responses={
            200: ChatSharedMediaResponseSerializer,
            404: OpenApiResponse(response=ApiErrorResponseSerializer),
        },
    )
    def get(self, request, establishment_id, conversation_id):
        membership = _resolve_membership(request, self.establishment_id)
        if isinstance(membership, Response):
            return membership
        conversation = get_conversation_for_participant(
            establishment_id=self.establishment_id,
            conversation_id=uuid.UUID(str(conversation_id)),
            membership_id=membership.id,
        )
        if conversation is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        queryset = (
            ChatMessageAttachment.objects.filter(
                message__conversation_id=conversation.id,
            )
            .select_related(
                "upload",
                "message__conversation",
                "message__author_membership",
                "message__author_membership__user",
            )
            .order_by("-created_at", "-id")
        )
        kind = request.query_params.get("kind")
        if kind:
            queryset = queryset.filter(kind=kind)
        raw_cursor = request.query_params.get("cursor")
        if raw_cursor:
            parts = raw_cursor.split("|", 1)
            if len(parts) != 2:
                return _chat_error_response(ChatValidationError("Invalid cursor."))
            from django.utils.dateparse import parse_datetime

            created_at = parse_datetime(parts[0])
            try:
                cursor_id = uuid.UUID(parts[1])
            except ValueError:
                return _chat_error_response(ChatValidationError("Invalid cursor."))
            if created_at is None:
                return _chat_error_response(ChatValidationError("Invalid cursor."))
            queryset = queryset.filter(
                models_q(created_at, cursor_id)
            )
        page = list(queryset[: CHAT_GALLERY_PAGE_SIZE + 1])
        has_more = len(page) > CHAT_GALLERY_PAGE_SIZE
        page = page[:CHAT_GALLERY_PAGE_SIZE]
        items = [serialize_attachment(attachment) for attachment in page]
        next_cursor = None
        if has_more and page:
            last = page[-1]
            next_cursor = f"{last.created_at.isoformat()}|{last.id}"
        return Response({"items": items, "has_more": has_more, "cursor": next_cursor})


def models_q(created_at, cursor_id):
    from django.db.models import Q

    return Q(created_at__lt=created_at) | Q(created_at=created_at, id__lt=cursor_id)
