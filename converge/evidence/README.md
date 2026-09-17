# Release evidence

Only evidence in a directory named for a currently documented release gate may
support a release claim. A directory whose name begins with `invalidated-` is
retained for auditability and is never release proof.

Every live-executor evidence set must identify the exact Converge, Seamwise,
and Task-Spec candidate commits and must have been produced by those immutable
candidates. Metadata alone does not establish that provenance.
