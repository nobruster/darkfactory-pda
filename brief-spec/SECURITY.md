# Security

## Supported versions

Security fixes are applied to the latest released minor version.

## Report a vulnerability

Use GitHub's private vulnerability reporting for this repository. Do not include credentials,
private transcripts, customer data, or exploit details in a public issue.

## Trust model

Brief-Spec hooks execute local code at agent lifecycle boundaries. Review the repository before
installation and use host-native hook trust controls. Brief-Spec is a presentation and validation
layer, not a security boundary.

The default runtime:

- makes no network requests;
- persists no raw prompts, transcripts, or tool results;
- treats transcript paths as untrusted and reads only a bounded tail;
- writes private, hashed session-state paths;
- fails open when a hook payload or state file cannot be safely processed;
- refuses to overwrite foreign installer files;
- removes only receipt-owned, unmodified files.

A syntactically valid brief can still contain an incorrect claim. Inspect authoritative evidence
for high-risk work.
