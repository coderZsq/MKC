# S5-10 Flutter Multiplatform Compatibility Checklist

Use this checklist before demo or release builds for iOS, Android, and Web.

## Scope

- Login and authenticated route guard.
- Resource list and content view.
- Upload entrypoint and file picker errors.
- Task status and progress.
- Chat, streaming answer, retry after disconnect, and citations.
- PDF page, SRT timestamp, and text citation navigation.

## Automated Checks

Run from `client/`:

```bash
flutter analyze
flutter test
flutter build web --dart-define=BASE_URL=https://mkc.example.com/api/v1
```

The Web build must not contain model provider keys, JWT secrets, database
passwords, private domains, or unredacted logs.

## Viewport Matrix

| Target | Width | Expected layout |
|---|---:|---|
| Mobile browser / phone | 390 | Single column, compact padding, upload actions stacked |
| Tablet | 834 | Single primary column with comfortable spacing |
| Desktop Web | 1440 | Centered content with max-width constraints |

## Platform Behavior

| Area | iOS / Android | Web |
|---|---|---|
| File picker | System picker, path-backed upload | Browser picker, in-memory bytes |
| Upload size | 500 MB limit | 100 MB limit to avoid browser memory pressure |
| SSE chat | Streaming when network supports it | Fetch stream with polling fallback |
| Citation jump | Route to content view with page/timestamp query | Same route, browser-safe relative URL |
| Safe area | Chat input and content avoid system insets | Browser viewport and narrow widths checked |

## Manual Smoke

1. Start the app against a local or demo Gateway.
2. Register or log in.
3. Open resource list.
4. Open upload page and cancel the picker.
5. Select a supported file and confirm task creation.
6. Open task center and task detail.
7. Open a conversation and send a question.
8. Disconnect/reconnect network or mock a stream failure; confirm retry appears.
9. Open an answer citation and confirm PDF page or SRT timestamp navigation.
10. Repeat the flow at mobile, tablet, and desktop widths.

## Known Issues

| Issue | Impact | Status |
|---|---|---|
| Real iOS/Android E2E requires simulator or device credentials | Not covered by CI | Manual release check |
| Web upload reads bytes in browser memory | Large files can fail earlier on Web | Limit documented at 100 MB |
| Production SSE depends on ingress buffering/timeouts | Stream may stall if ingress is misconfigured | Covered by S5-8 deployment runbook |
| Public demo domain is environment-specific | Web build command uses placeholder domain | Replace before release |
