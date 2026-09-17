# SHA-256 sidecar contract

The sidecar is ASCII and contains exactly one line:

```text
<64 lowercase hexadecimal SHA-256 characters><two spaces><artifact basename><LF>
```

The filename is a basename, not a path. Its digest must equal both the
transported artifact bytes and the corresponding manifest field.

