from __future__ import annotations

import uuid

from django.conf import settings
from django.http import FileResponse, Http404, HttpResponseRedirect
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import permissions, status
from rest_framework.parsers import BaseParser
from rest_framework.response import Response
from rest_framework.views import APIView

from houston.accounts.api.serializers import ApiErrorResponseSerializer, DetailResponseSerializer
from houston.accounts.authentication import BearerAccessTokenAuthentication
from houston.comments.api.serializers import (
    ActionPlanCommentReserveUploadRequestSerializer,
    ActionPlanCommentReserveUploadResponseSerializer,
    ActionPlanCommentUploadCompleteResponseSerializer,
)
from houston.comments.exceptions import CommentValidationError
from houston.comments.models import ActionPlanCommentAttachment
from houston.comments.selectors import get_action_plan_execution_for_comments
from houston.comments.upload_services import (
    build_action_plan_comment_upload_put_url,
    complete_action_plan_comment_upload,
    execution_comment_attachments_are_available,
    generate_action_plan_comment_attachment_presigned_get,
    get_reserved_action_plan_comment_upload,
    reserve_action_plan_comment_upload,
    store_action_plan_comment_upload_content,
)
from houston.establishments.permissions import HasActiveMembership
from houston.uploads.access import resolve_observation_actor_membership
from houston.uploads.api.views import EstablishmentScopedObservationMixin
from houston.uploads.private_storage import (
    PRIVATE_MEDIA_BACKEND_S3,
    get_action_plan_comment_private_media_storage,
)


class _RawBodyParser(BaseParser):
    media_type = "*/*"

    def parse(self, stream, media_type=None, parser_context=None):
        return stream.read()


def _is_s3() -> bool:
    backend = getattr(settings, "HOUSTON_PRIVATE_MEDIA_BACKEND", "")
    return (backend or "").strip().lower() == PRIVATE_MEDIA_BACKEND_S3


def _load_execution(request, establishment_id, execution_id):
    membership = resolve_observation_actor_membership(
        request,
        establishment_id=establishment_id,
    )
    if membership is None:
        return None, None
    execution = get_action_plan_execution_for_comments(
        membership=membership,
        execution_id=uuid.UUID(str(execution_id)),
    )
    if execution is None:
        return None, None
    return membership, execution


def _validation_error_response(exc: CommentValidationError) -> Response:
    return Response(
        {"code": "validation_error", "detail": exc.detail},
        status=status.HTTP_400_BAD_REQUEST,
    )


class ActionPlanCommentReserveUploadView(EstablishmentScopedObservationMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, HasActiveMembership]

    @extend_schema(
        tags=["comments"],
        request=ActionPlanCommentReserveUploadRequestSerializer,
        responses={
            201: ActionPlanCommentReserveUploadResponseSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            401: OpenApiResponse(response=DetailResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
        },
    )
    def post(self, request, establishment_id, execution_id):
        membership, execution = _load_execution(request, self.establishment_id, execution_id)
        if membership is None or execution is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        body = ActionPlanCommentReserveUploadRequestSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        try:
            upload = reserve_action_plan_comment_upload(
                actor_membership=membership,
                execution=execution,
                original_filename=body.validated_data["filename"],
                content_type=body.validated_data["content_type"],
                size_bytes=body.validated_data["size_bytes"],
            )
        except CommentValidationError as exc:
            return _validation_error_response(exc)
        return Response(
            ActionPlanCommentReserveUploadResponseSerializer(
                {
                    "upload_id": upload.id,
                    "put_url": build_action_plan_comment_upload_put_url(upload=upload),
                    "expires_at": upload.expires_at,
                }
            ).data,
            status=status.HTTP_201_CREATED,
        )


class ActionPlanCommentUploadContentView(EstablishmentScopedObservationMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, HasActiveMembership]
    parser_classes = [_RawBodyParser]

    @extend_schema(
        tags=["comments"],
        request=None,
        responses={
            204: OpenApiResponse(description="Content stored."),
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
        },
    )
    def put(self, request, establishment_id, execution_id, upload_id):
        if _is_s3():
            return Response(
                {"code": "validation_error", "detail": "Use the presigned PUT URL."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        membership, execution = _load_execution(request, self.establishment_id, execution_id)
        if membership is None or execution is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        payload = request.data if isinstance(request.data, (bytes, bytearray)) else request.body
        try:
            upload = get_reserved_action_plan_comment_upload(
                actor_membership=membership,
                execution=execution,
                upload_id=uuid.UUID(str(upload_id)),
            )
            store_action_plan_comment_upload_content(upload=upload, payload=bytes(payload))
        except CommentValidationError as exc:
            return _validation_error_response(exc)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ActionPlanCommentRefreshUploadPresignView(EstablishmentScopedObservationMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, HasActiveMembership]

    @extend_schema(
        tags=["comments"],
        request=None,
        responses={
            200: ActionPlanCommentReserveUploadResponseSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
        },
    )
    def post(self, request, establishment_id, execution_id, upload_id):
        membership, execution = _load_execution(request, self.establishment_id, execution_id)
        if membership is None or execution is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        try:
            upload = get_reserved_action_plan_comment_upload(
                actor_membership=membership,
                execution=execution,
                upload_id=uuid.UUID(str(upload_id)),
            )
        except CommentValidationError as exc:
            return _validation_error_response(exc)
        return Response(
            ActionPlanCommentReserveUploadResponseSerializer(
                {
                    "upload_id": upload.id,
                    "put_url": build_action_plan_comment_upload_put_url(upload=upload),
                    "expires_at": upload.expires_at,
                }
            ).data
        )


class ActionPlanCommentCompleteUploadView(EstablishmentScopedObservationMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, HasActiveMembership]

    @extend_schema(
        tags=["comments"],
        request=None,
        responses={
            200: ActionPlanCommentUploadCompleteResponseSerializer,
            400: OpenApiResponse(response=ApiErrorResponseSerializer),
            404: OpenApiResponse(response=DetailResponseSerializer),
        },
    )
    def post(self, request, establishment_id, execution_id, upload_id):
        membership, execution = _load_execution(request, self.establishment_id, execution_id)
        if membership is None or execution is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        try:
            upload = complete_action_plan_comment_upload(
                actor_membership=membership,
                execution=execution,
                upload_id=uuid.UUID(str(upload_id)),
            )
        except CommentValidationError as exc:
            return _validation_error_response(exc)
        return Response(
            ActionPlanCommentUploadCompleteResponseSerializer(
                {
                    "upload_id": upload.id,
                    "status": upload.status,
                    "kind": upload.kind,
                    "content_type": upload.content_type,
                    "size_bytes": upload.size_bytes,
                }
            ).data
        )


class ActionPlanCommentAttachmentPreviewView(EstablishmentScopedObservationMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, HasActiveMembership]

    @extend_schema(
        tags=["comments"],
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
    def get(self, request, establishment_id, execution_id, attachment_id):
        membership, execution = _load_execution(request, self.establishment_id, execution_id)
        if membership is None or execution is None:
            raise Http404
        if not execution_comment_attachments_are_available(execution):
            raise Http404
        attachment = (
            ActionPlanCommentAttachment.objects.select_related("upload", "comment")
            .filter(
                id=attachment_id,
                action_plan_execution_id=execution.id,
                upload__establishment_id=self.establishment_id,
            )
            .first()
        )
        if attachment is None:
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
            url = generate_action_plan_comment_attachment_presigned_get(storage_key=storage_key)
            response = HttpResponseRedirect(url)
            response["Referrer-Policy"] = "no-referrer"
            response["Cache-Control"] = "private, max-age=60, must-revalidate"
            return response
        storage = get_action_plan_comment_private_media_storage()
        if not storage.exists(storage_key):
            raise Http404
        handle = storage.open(storage_key, "rb")
        response = FileResponse(handle, content_type=content_type)
        response["Referrer-Policy"] = "no-referrer"
        response["Cache-Control"] = "private, max-age=60, must-revalidate"
        return response
