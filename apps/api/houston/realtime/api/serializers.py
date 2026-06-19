from rest_framework import serializers


class RealtimeWsTicketResponseSerializer(serializers.Serializer):
    ticket = serializers.CharField()
    expires_in = serializers.IntegerField()
