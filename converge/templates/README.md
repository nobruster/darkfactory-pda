# Templates

The workspace scaffold `cvg init` projects into a consumer repository. These are
copied verbatim, so a change here changes what every future `cvg init` creates.

`workspace/` becomes `cvg/` in the target project: `INDEX.md` is the operator's
entry point, and the two `*-README.md` files explain the `tasks/` and `receipts/`
directories once they exist.

`cvg init` is non-clobbering — it never overwrites a file the consumer already
has, so editing a template does not retroactively change existing workspaces.
