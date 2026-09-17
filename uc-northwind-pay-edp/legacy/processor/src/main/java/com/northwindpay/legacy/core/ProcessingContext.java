package com.northwindpay.legacy.core;

import com.fasterxml.jackson.databind.JsonNode;

import java.nio.file.Path;

/**
 * Integrity-checked inputs and runtime boundaries supplied to a typed
 * processor.
 */
public record ProcessingContext(
        String batchId,
        Configuration configuration,
        ArtifactGateway artifactGateway,
        Path workingDirectory,
        byte[] sourceManifestBytes,
        JsonNode sourceManifest,
        SourceArtifact sourceArtifact) {

    /**
     * Defensively owns source bytes at the shared boundary.
     */
    public ProcessingContext {
        sourceManifestBytes = sourceManifestBytes.clone();
    }

    @Override
    public byte[] sourceManifestBytes() {
        return sourceManifestBytes.clone();
    }

    /**
     * Raw source artifact whose size, hash, and checksum sidecar agree.
     */
    public record SourceArtifact(
            String filename,
            String sha256,
            long sizeBytes,
            byte[] bytes) {

        public SourceArtifact {
            bytes = bytes.clone();
        }

        @Override
        public byte[] bytes() {
            return bytes.clone();
        }
    }
}
