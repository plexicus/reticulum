//! Resource discovery sources beyond Helm: raw Kubernetes manifests and
//! docker-compose stacks. Each source contributes config units (Charts with a
//! SourceKind) and, when needed, Service entries so findings can attach.

pub mod compose;
pub mod k8s;
