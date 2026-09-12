"""Outbound pings. Two channels, both optional and both truthful:

  publish_sns  the unattended run's "one thing needs you" ping (an SNS topic
               with an email subscription is the demo's notification channel)
  send_email   an approved attorney draft delivered through Amazon SES

Neither function raises: a failed send comes back as PingResult(sent=False,
error=...), so the caller can label the outcome instead of crashing, and
the UI never claims a message went out when it did not.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import boto3


@dataclass
class PingResult:
    sent: bool
    channel: str  # "sns" | "ses"
    target: str | None
    message_id: str | None = None
    error: str | None = None

    def as_dict(self) -> dict:
        return asdict(self)


def publish_sns(topic_arn: str, subject: str, body: str, client=None, region_name: str = "us-east-1") -> PingResult:
    client = client or boto3.client("sns", region_name=region_name)
    try:
        response = client.publish(TopicArn=topic_arn, Subject=subject[:100], Message=body)
    except Exception as exc:  # noqa: BLE001 - report, never raise
        return PingResult(sent=False, channel="sns", target=topic_arn, error=f"{type(exc).__name__}: {exc}"[:300])
    return PingResult(sent=True, channel="sns", target=topic_arn, message_id=response.get("MessageId"))


def send_email(sender: str, to: str, subject: str, body: str, client=None, region_name: str = "us-east-1") -> PingResult:
    client = client or boto3.client("sesv2", region_name=region_name)
    try:
        response = client.send_email(
            FromEmailAddress=sender,
            Destination={"ToAddresses": [to]},
            Content={"Simple": {"Subject": {"Data": subject}, "Body": {"Text": {"Data": body}}}},
        )
    except Exception as exc:  # noqa: BLE001
        return PingResult(sent=False, channel="ses", target=to, error=f"{type(exc).__name__}: {exc}"[:300])
    return PingResult(sent=True, channel="ses", target=to, message_id=response.get("MessageId"))
