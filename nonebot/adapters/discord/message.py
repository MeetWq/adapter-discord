from collections.abc import Iterable
from dataclasses import dataclass
import datetime
import re
from typing import (
    TYPE_CHECKING,
    Any,
    Literal,
    Optional,
    TypedDict,
    Union,
    overload,
)
from typing_extensions import Self, override

from nonebot.adapters import (
    Message as BaseMessage,
    MessageSegment as BaseMessageSegment,
)
from nonebot.compat import type_validate_python

from .api import (
    UNSET,
    ActionRow,
    AttachmentSend,
    Button,
    Component,
    ComponentType,
    DirectComponent,
    Embed,
    File,
    MessageGet,
    MessageReference,
    SelectMenu,
    Snowflake,
    SnowflakeType,
    TextInput,
    TimeStampStyle,
)
from .utils import unescape


class MessageSegment(BaseMessageSegment["Message"]):
    @classmethod
    @override
    def get_message_class(cls) -> type["Message"]:
        return Message

    @staticmethod
    def attachment(
        file: Union[str, File, AttachmentSend],
        description: Optional[str] = None,
        content: Optional[bytes] = None,
    ) -> "AttachmentSegment":
        if isinstance(file, str):
            _filename = file
            _description = description
            _content = content
        elif isinstance(file, File):
            _filename = file.filename
            _description = description
            _content = file.content
        elif isinstance(file, AttachmentSend):
            _filename = file.filename
            _description = file.description
            _content = content
        else:
            raise TypeError("file must be str, File or AttachmentSend")
        if _content is None:
            return AttachmentSegment(
                "attachment",
                {
                    "attachment": AttachmentSend(
                        filename=_filename, description=_description
                    ),
                    "file": None,
                },
            )
        else:
            return AttachmentSegment(
                "attachment",
                {
                    "attachment": AttachmentSend(
                        filename=_filename, description=_description
                    ),
                    "file": File(filename=_filename, content=_content),
                },
            )

    @staticmethod
    def sticker(sticker_id: SnowflakeType) -> "StickerSegment":
        return StickerSegment("sticker", {"id": Snowflake(sticker_id)})

    @staticmethod
    def embed(embed: Embed) -> "EmbedSegment":
        return EmbedSegment("embed", {"embed": embed})

    @staticmethod
    def component(component: Component):
        if isinstance(component, (Button, SelectMenu)):
            component_ = ActionRow(components=[component])
        else:
            component_ = component
        return ComponentSegment("component", {"component": component_})

    @staticmethod
    def custom_emoji(
        name: str, emoji_id: str, animated: Optional[bool] = None
    ) -> "CustomEmojiSegment":
        return CustomEmojiSegment(
            "custom_emoji", {"name": name, "id": emoji_id, "animated": animated}
        )

    @staticmethod
    def mention_user(user_id: SnowflakeType) -> "MentionUserSegment":
        return MentionUserSegment("mention_user", {"user_id": Snowflake(user_id)})

    @staticmethod
    def mention_role(role_id: SnowflakeType) -> "MentionRoleSegment":
        return MentionRoleSegment("mention_role", {"role_id": Snowflake(role_id)})

    @staticmethod
    def mention_channel(channel_id: SnowflakeType) -> "MentionChannelSegment":
        return MentionChannelSegment(
            "mention_channel", {"channel_id": Snowflake(channel_id)}
        )

    @staticmethod
    def mention_everyone() -> "MentionEveryoneSegment":
        return MentionEveryoneSegment("mention_everyone")

    @staticmethod
    def text(content: str) -> "TextSegment":
        return TextSegment("text", {"text": content})

    @staticmethod
    def timestamp(
        timestamp: Union[int, datetime.datetime], style: Optional[TimeStampStyle] = None
    ) -> "TimestampSegment":
        if isinstance(timestamp, datetime.datetime):
            timestamp = int(timestamp.timestamp())
        return TimestampSegment("timestamp", {"timestamp": timestamp, "style": style})

    @staticmethod
    @overload
    def reference(reference: MessageReference) -> "ReferenceSegment": ...

    @staticmethod
    @overload
    def reference(
        reference: SnowflakeType,
        channel_id: Optional[SnowflakeType] = None,
        guild_id: Optional[SnowflakeType] = None,
        fail_if_not_exists: Optional[bool] = None,
    ) -> "ReferenceSegment": ...

    @staticmethod
    def reference(
        reference: Union[SnowflakeType, MessageReference],
        channel_id: Optional[SnowflakeType] = None,
        guild_id: Optional[SnowflakeType] = None,
        fail_if_not_exists: Optional[bool] = None,
    ):
        if isinstance(reference, MessageReference):
            _reference = reference
        else:
            _reference = MessageReference(
                message_id=Snowflake(reference) if reference else UNSET,
                channel_id=Snowflake(channel_id) if channel_id else UNSET,
                guild_id=Snowflake(guild_id) if guild_id else UNSET,
                fail_if_not_exists=fail_if_not_exists or UNSET,
            )

        return ReferenceSegment("reference", {"reference": _reference})

    @override
    def is_text(self) -> bool:
        return self.type == "text"

    @classmethod
    @override
    def _validate(cls, value) -> Self:
        if isinstance(value, cls):
            return value
        if isinstance(value, MessageSegment):
            raise ValueError(f"Type {type(value)} can not be converted to {cls}")
        if not isinstance(value, dict):
            raise ValueError(f"Expected dict for MessageSegment, got {type(value)}")
        if "type" not in value:
            raise ValueError(
                f"Expected dict with 'type' for MessageSegment, got {value}"
            )
        _type = value["type"]
        if _type not in SEGMENT_TYPE_MAP:
            raise ValueError(f"Invalid MessageSegment type: {_type}")
        segment_type = SEGMENT_TYPE_MAP[_type]

        # casting value to subclass of MessageSegment
        if cls is MessageSegment:
            return type_validate_python(segment_type, value)
        # init segment instance directly if type matched
        if cls is segment_type:
            return segment_type(type=_type, data=value.get("data", {}))
        raise ValueError(f"Segment type {_type!r} can not be converted to {cls}")


class StickerData(TypedDict):
    id: Snowflake


@dataclass
class StickerSegment(MessageSegment):
    if TYPE_CHECKING:
        type: Literal["sticker"]
        data: StickerData

    @override
    def __str__(self) -> str:
        return f"<Sticker:{self.data['id']}>"


class ComponentData(TypedDict):
    component: DirectComponent


@dataclass
class ComponentSegment(MessageSegment):
    if TYPE_CHECKING:
        type: Literal["component"]
        data: ComponentData

    @override
    def __str__(self) -> str:
        return f"<Component:{self.data['component'].type}>"

    @classmethod
    @override
    def _validate(cls, value) -> Self:
        instance = super()._validate(value)
        if "component" not in instance.data:
            raise ValueError(
                f"Expected dict with 'component' in 'data' for ComponentSegment, got {value}"
            )
        if not isinstance(
            component := instance.data["component"], (ActionRow, TextInput)
        ):
            if not isinstance(component, dict):
                raise ValueError(
                    f"Expected dict for ComponentData, got {type(component)}"
                )
            if "type" not in component:
                raise ValueError(
                    f"Expected dict with 'type' for ComponentData, got {component}"
                )
            if component["type"] == ComponentType.ActionRow:
                instance.data["component"] = type_validate_python(ActionRow, component)
            elif component["type"] == ComponentType.TextInput:
                instance.data["component"] = type_validate_python(TextInput, component)
            else:
                raise ValueError(f"Invalid ComponentType: {component['type']}")
        return instance


class CustomEmojiData(TypedDict):
    name: str
    id: str
    animated: Optional[bool]


@dataclass
class CustomEmojiSegment(MessageSegment):
    if TYPE_CHECKING:
        type: Literal["custom_emoji"]
        data: CustomEmojiData

    @override
    def __str__(self) -> str:
        if self.data.get("animated"):
            return f"<a:{self.data['name']}:{self.data['id']}>"
        else:
            return f"<:{self.data['name']}:{self.data['id']}>"


class MentionUserData(TypedDict):
    user_id: Snowflake


@dataclass
class MentionUserSegment(MessageSegment):
    if TYPE_CHECKING:
        type: Literal["mention_user"]
        data: MentionUserData

    @override
    def __str__(self) -> str:
        return f"<@{self.data['user_id']}>"


class MentionChannelData(TypedDict):
    channel_id: Snowflake


@dataclass
class MentionChannelSegment(MessageSegment):
    if TYPE_CHECKING:
        type: Literal["mention_channel"]
        data: MentionChannelData

    @override
    def __str__(self) -> str:
        return f"<#{self.data['channel_id']}>"


class MentionRoleData(TypedDict):
    role_id: Snowflake


@dataclass
class MentionRoleSegment(MessageSegment):
    if TYPE_CHECKING:
        type: Literal["mention_role"]
        data: MentionRoleData

    @override
    def __str__(self) -> str:
        return f"<@&{self.data['role_id']}>"


@dataclass
class MentionEveryoneSegment(MessageSegment):
    if TYPE_CHECKING:
        type: Literal["mention_everyone"]

    @override
    def __str__(self) -> str:
        return "@everyone"


class TimestampData(TypedDict):
    timestamp: int
    style: Optional[TimeStampStyle]


@dataclass
class TimestampSegment(MessageSegment):
    if TYPE_CHECKING:
        type: Literal["timestamp"]
        data: TimestampData

    @override
    def __str__(self) -> str:
        style = self.data.get("style")
        return (
            f"<t:{self.data['timestamp']}"
            + (
                f":{style.value if isinstance(style, TimeStampStyle) else style}"
                if style
                else ""
            )
            + ">"
        )


class TextData(TypedDict):
    text: str


@dataclass
class TextSegment(MessageSegment):
    if TYPE_CHECKING:
        type: Literal["text"]
        data: TextData

    @override
    def __str__(self) -> str:
        return self.data["text"]


class EmbedData(TypedDict):
    embed: Embed


@dataclass
class EmbedSegment(MessageSegment):
    if TYPE_CHECKING:
        type: Literal["embed"]
        data: EmbedData

    @override
    def __str__(self) -> str:
        return f"<Embed:{self.data['embed'].type}>"

    @classmethod
    @override
    def _validate(cls, value) -> Self:
        instance = super()._validate(value)
        if "embed" not in instance.data:
            raise ValueError(
                f"Expected dict with 'embed' in 'data' for EmbedSegment, got {value}"
            )
        if not isinstance(embed := instance.data["embed"], Embed):
            instance.data["embed"] = type_validate_python(Embed, embed)
        return instance


class AttachmentData(TypedDict):
    attachment: AttachmentSend
    file: Optional[File]


@dataclass
class AttachmentSegment(MessageSegment):
    if TYPE_CHECKING:
        type: Literal["attachment"]
        data: AttachmentData

    @override
    def __str__(self) -> str:
        return f"<Attachment:{self.data['attachment'].filename}>"

    @classmethod
    @override
    def _validate(cls, value) -> Self:
        instance = super()._validate(value)
        if "attachment" not in instance.data:
            raise ValueError(
                f"Expected dict with 'attachment' in 'data' for AttachmentSegment, got {value}"
            )
        if not isinstance(attachment := instance.data["attachment"], AttachmentSend):
            instance.data["attachment"] = type_validate_python(
                AttachmentSend, attachment
            )
        if (file := instance.data.get("file")) is not None and not isinstance(
            file, File
        ):
            instance.data["file"] = type_validate_python(File, file)
        return instance


class ReferenceData(TypedDict):
    reference: MessageReference


@dataclass
class ReferenceSegment(MessageSegment):
    if TYPE_CHECKING:
        type: Literal["reference"]
        data: ReferenceData

    @override
    def __str__(self):
        return f"<Reference:{self.data['reference'].message_id}>"

    @classmethod
    @override
    def _validate(cls, value) -> Self:
        instance = super()._validate(value)
        if "reference" not in instance.data:
            raise ValueError(
                f"Expected dict with 'reference' in 'data' for ReferenceSegment, got {value}"
            )
        if not isinstance(reference := instance.data["reference"], MessageReference):
            instance.data["reference"] = type_validate_python(
                MessageReference, reference
            )
        return instance


SEGMENT_TYPE_MAP = {
    "attachment": AttachmentSegment,
    "sticker": StickerSegment,
    "embed": EmbedSegment,
    "component": ComponentSegment,
    "custom_emoji": CustomEmojiSegment,
    "mention_user": MentionUserSegment,
    "mention_role": MentionRoleSegment,
    "mention_channel": MentionChannelSegment,
    "mention_everyone": MentionEveryoneSegment,
    "text": TextSegment,
    "timestamp": TimestampSegment,
    "reference": ReferenceSegment,
}


class Message(BaseMessage[MessageSegment]):
    @classmethod
    @override
    def get_segment_class(cls) -> type[MessageSegment]:
        return MessageSegment

    @override
    def __add__(
        self, other: Union[str, MessageSegment, Iterable[MessageSegment]]
    ) -> "Message":
        return super().__add__(
            MessageSegment.text(other) if isinstance(other, str) else other
        )

    @override
    def __radd__(
        self, other: Union[str, MessageSegment, Iterable[MessageSegment]]
    ) -> "Message":
        return super().__radd__(
            MessageSegment.text(other) if isinstance(other, str) else other
        )

    @staticmethod
    @override
    def _construct(msg: str) -> Iterable[MessageSegment]:
        text_begin = 0
        for embed in re.finditer(
            r"<(?P<type>(@!|@&|@|#|/|:|a:|t:))(?P<param>[^<]+?)>",
            msg,
        ):
            if content := msg[text_begin : embed.pos + embed.start()]:
                yield MessageSegment.text(unescape(content))
            text_begin = embed.pos + embed.end()
            if embed.group("type") in ("@!", "@"):
                yield MessageSegment.mention_user(Snowflake(embed.group("param")))
            elif embed.group("type") == "@&":
                yield MessageSegment.mention_role(Snowflake(embed.group("param")))
            elif embed.group("type") == "#":
                yield MessageSegment.mention_channel(Snowflake(embed.group("param")))
            elif embed.group("type") == "/":
                # TODO: slash command
                pass
            elif embed.group("type") in (":", "a:"):
                if len(cut := embed.group("param").split(":")) == 2:
                    yield MessageSegment.custom_emoji(
                        cut[0], cut[1], embed.group("type") == "a:"
                    )
                else:
                    yield MessageSegment.text(unescape(embed.group()))
            else:
                if (
                    len(cut := embed.group("param").split(":")) == 2
                    and cut[0].isdigit()
                ):
                    yield MessageSegment.timestamp(int(cut[0]), TimeStampStyle(cut[1]))
                elif embed.group().isdigit():
                    yield MessageSegment.timestamp(int(embed.group()))
                else:
                    yield MessageSegment.text(unescape(embed.group()))
        if content := msg[text_begin:]:
            yield MessageSegment.text(unescape(content))

    @classmethod
    def from_guild_message(cls, message: MessageGet) -> "Message":
        msg = Message()
        if message.mention_everyone:
            msg.append(MessageSegment.mention_everyone())
        if message.content:
            msg.extend(Message(message.content))
        if message.attachments:
            msg.extend(
                MessageSegment.attachment(
                    AttachmentSend(
                        filename=attachment.filename,
                        description=(
                            attachment.description
                            if isinstance(attachment.description, str)
                            else None
                        ),
                    )
                )
                for attachment in message.attachments
            )
        if message.embeds:
            msg.extend(MessageSegment.embed(embed) for embed in message.embeds)
        if message.components:
            msg.extend(
                MessageSegment.component(component) for component in message.components
            )
        return msg

    def extract_content(self) -> str:
        return "".join(
            str(seg)
            for seg in self
            if seg.type
            in (
                "text",
                "custom_emoji",
                "mention_user",
                "mention_role",
                "mention_everyone",
                "mention_channel",
                "timestamp",
            )
        )


def parse_message(message: Union[Message, MessageSegment, str]) -> dict[str, Any]:
    message = MessageSegment.text(message) if isinstance(message, str) else message
    message = message if isinstance(message, Message) else Message(message)

    content = message.extract_content() or None
    if embeds := (message["embed"] or None):
        embeds = [embed.data["embed"] for embed in embeds]
    if reference := (message["reference"] or None):
        reference = reference[-1].data["reference"]
    if components := (message["component"] or None):
        components = [component.data["component"] for component in components]
    if sticker_ids := (message["sticker"] or None):
        sticker_ids = [sticker.data["id"] for sticker in sticker_ids]

    attachments = None
    files = None
    if attachments_segment := (message["attachment"] or None):
        attachments = [
            attachment.data["attachment"] for attachment in attachments_segment
        ]
        files = [
            attachment.data["file"]
            for attachment in attachments_segment
            if attachment.data["file"] is not None
        ]
    return {
        k: v
        for k, v in {
            "content": content,
            "embeds": embeds,
            "message_reference": reference,
            "components": components,
            "sticker_ids": sticker_ids,
            "files": files,
            "attachments": attachments,
        }.items()
        if v is not None
    }
