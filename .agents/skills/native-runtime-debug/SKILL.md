---
name: native-runtime-debug
description: Diagnose behavior that differs between Spore Web and Native/Capacitor runtimes by identifying the actual runtime boundary and owning layer before fixing it.
---

# Native runtime debug

Provide Native-runtime diagnostic expertise. This skill does not expand the permissions or scope of the active workflow.

Read the applicable `AGENTS.md` and establish the expected behavior before diagnosing the divergence.

Native is a product runtime, not a responsive breakpoint. A large Native viewport does not become desktop Web.

Establish the Web/Native difference from available evidence and reproduce it when the available runtime permits it. Never claim device reproduction or validation from code inspection, build success, simulator behavior, or runtime assumptions alone.

First determine whether the failure is actually runtime-specific. If Web and Native fail the same way, investigate shared feature, state, navigation, data, or shell ownership before creating a runtime branch.

When only Native is affected, identify the concrete runtime capability, lifecycle, OS, or bridge difference that explains the divergence.

Consider the narrowest relevant owner:

- runtime or build configuration;
- shell, viewport, safe area, keyboard, scrolling, or layout;
- navigation, deep links, or system back;
- auth or session transport;
- network or foreground/background lifecycle;
- native plugin or Capacitor bridge;
- shared feature or data-access code.

Confirm actual runtime state rather than inferring it from viewport or command name. Distinguish Web, a build pinned with `VITE_APP_RUNTIME=native`, and execution on a real Capacitor native platform.

Gather evidence appropriate to the failure before proposing a correction.

For layout, keyboard, or viewport failures, identify the actual scroll/layout owner and gather viewport or geometry evidence before changing global positioning, overflow, or height behavior.

For auth, network, lifecycle, deep-link, secure-storage, or plugin failures, inspect the owning transport or Native boundary rather than compensating in feature UI.

Runtime branching must correspond to a demonstrated runtime difference, not merely to platform identity.

Keep runtime-specific logic concentrated at established runtime, shell, navigation, auth, or plugin boundaries. Do not scatter Native/Desktop checks through feature trees.

Do not duplicate shared product behavior across Web desktop and Native/mobile when the responsibility remains common.

Do not introduce a browser fallback as a substitute for a required Native capability unless the product explicitly supports that fallback.

Spore is not a PWA. Do not introduce service-worker, web-manifest, or PWA behavior as a Native-runtime fix.

API and WebSocket host resolution must remain owned by runtime configuration rather than feature code.

Web and Native authentication may use different transports, but feature code must not own credential-storage details or create parallel authentication models.

Fix or recommend the narrowest owner that explains the divergence. Avoid local workarounds when evidence points to a shared runtime, shell, navigation, or state defect.

Validate on the runtime that actually matters. Explicitly report what still requires simulator, emulator, physical-device, OS-level, or external-service verification.

Output:

## Diagnosis

State the owning layer and whether the defect is genuinely runtime-specific or shared.

## Evidence

Report only evidence actually observed.

## Correction

Describe or apply the narrowest correction allowed by the active workflow.

## Validation gap

State what remains unverified and which runtime or device is required.