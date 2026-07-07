package model

import (
	"reflect"
	"strings"
	"testing"
)

func assertTag(t *testing.T, field reflect.StructTag, name, want string) {
	t.Helper()
	got := field.Get(name)
	if !strings.Contains(got, want) {
		t.Errorf("tag %q missing %q, got %q", name, want, got)
	}
}

func tagOf(t *testing.T, rt reflect.Type, name string) reflect.StructTag {
	t.Helper()
	f, ok := rt.FieldByName(name)
	if !ok {
		t.Fatalf("field %q not found", name)
	}
	return f.Tag
}

func TestUserTags(t *testing.T) {
	var u User
	rv := reflect.TypeOf(u)
	assertTag(t, tagOf(t, rv, "Email"), "gorm", "uniqueIndex:uk_users_email")
	assertTag(t, tagOf(t, rv, "UUID"), "gorm", "uniqueIndex:uk_users_uuid")
	assertTag(t, tagOf(t, rv, "Status"), "gorm", "default:1")
	assertTag(t, tagOf(t, rv, "DeletedAt"), "gorm", "index")
}

func TestResourceTags(t *testing.T) {
	var r Resource
	rv := reflect.TypeOf(r)
	assertTag(t, tagOf(t, rv, "UUID"), "gorm", "uniqueIndex:uk_resources_uuid")
	assertTag(t, tagOf(t, rv, "UserID"), "gorm", "index:idx_resources_user_id")
	assertTag(t, tagOf(t, rv, "UserID"), "gorm", "index:idx_resources_user_status")
	assertTag(t, tagOf(t, rv, "Type"), "gorm", "index:idx_resources_type")
	assertTag(t, tagOf(t, rv, "User"), "gorm", "OnDelete:CASCADE")
}

func TestTaskTags(t *testing.T) {
	var tk Task
	rv := reflect.TypeOf(tk)
	assertTag(t, tagOf(t, rv, "UUID"), "gorm", "uniqueIndex:uk_tasks_uuid")
	assertTag(t, tagOf(t, rv, "Status"), "gorm", "default:pending")
	assertTag(t, tagOf(t, rv, "UserID"), "gorm", "index:idx_tasks_user_status")
	assertTag(t, tagOf(t, rv, "Resource"), "gorm", "OnDelete:CASCADE")
}

func TestConversationTags(t *testing.T) {
	var c Conversation
	rv := reflect.TypeOf(c)
	assertTag(t, tagOf(t, rv, "UUID"), "gorm", "uniqueIndex:uk_conversations_uuid")
	assertTag(t, tagOf(t, rv, "UserID"), "gorm", "index:idx_conversations_user_id")
	assertTag(t, tagOf(t, rv, "User"), "gorm", "OnDelete:CASCADE")
}

func TestMessageTags(t *testing.T) {
	var m Message
	rv := reflect.TypeOf(m)
	assertTag(t, tagOf(t, rv, "UUID"), "gorm", "uniqueIndex:uk_messages_uuid")
	assertTag(t, tagOf(t, rv, "ConversationID"), "gorm", "index:idx_messages_conversation_id")
	assertTag(t, tagOf(t, rv, "ConversationID"), "gorm", "index:idx_messages_conversation_created")
	assertTag(t, tagOf(t, rv, "Conversation"), "gorm", "OnDelete:CASCADE")
}
