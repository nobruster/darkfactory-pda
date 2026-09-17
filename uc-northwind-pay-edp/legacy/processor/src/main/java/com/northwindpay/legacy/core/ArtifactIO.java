package com.northwindpay.legacy.core;

import com.fasterxml.jackson.databind.JsonNode;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.GeneralSecurityException;
import java.security.MessageDigest;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.regex.Pattern;

/**
 * Shared source acquisition and manifest-last sanitized publication.
 */
public final class ArtifactIO {
    private static final int MAX_MANIFEST_BYTES = 1_000_000;
    private static final Pattern BATCH_PATTERN = Pattern.compile("B[0-9]{15}");
    private static final Pattern SAFE_FILENAME =
            Pattern.compile("[A-Za-z0-9][A-Za-z0-9._-]{0,254}");

    private ArtifactIO() {
    }

    /**
     * Downloads the source manifest, raw artifact, and checksum sidecar, then
     * verifies byte size and both SHA-256 declarations before parsing begins.
     */
    public static ProcessingContext acquire(
            String batchId,
            Configuration configuration,
            ArtifactGateway artifactGateway,
            Path workingDirectory) throws ProcessorException {
        if (batchId == null || !BATCH_PATTERN.matcher(batchId).matches()) {
            throw new ProcessorException(
                    "INVALID_BATCH_ID",
                    "Batch ID does not match the legacy contract");
        }

        Path manifestPath = workingDirectory.resolve("source-manifest.json");
        String sourceDirectory = "/raw/processing/" + batchId;
        artifactGateway.download(
                sourceDirectory + "/source-manifest.json",
                manifestPath);

        byte[] manifestBytes = readBytes(manifestPath);
        if (manifestBytes.length == 0
                || manifestBytes.length > MAX_MANIFEST_BYTES) {
            throw new ProcessorException(
                    "INVALID_MANIFEST",
                    "Source manifest size is invalid");
        }
        JsonNode manifest = StableJson.parse(manifestBytes);
        JsonNode fileType = manifest.path("file_type");
        JsonNode sourceFile = manifest.path("source_file");
        String filename = sourceFile.path("name").asText();
        String sourceSha256 = sourceFile.path("sha256").asText();
        long sizeBytes = sourceFile.path("size_bytes").asLong(-1);

        if (!manifest.isObject()
                || !manifest.path("schema_version").isIntegralNumber()
                || manifest.path("schema_version").intValue() != 1
                || !manifest.path("batch_id").isTextual()
                || !batchId.equals(manifest.path("batch_id").asText())
                || !fileType.isObject()
                || !fileType.path("number").isTextual()
                || !fileType.path("number").asText().matches("[0-9]{2}")
                || !sourceFile.isObject()
                || !sourceFile.path("name").isTextual()
                || !SAFE_FILENAME.matcher(filename).matches()
                || !sourceFile.path("sha256").isTextual()
                || !sourceSha256.matches("[0-9a-f]{64}")
                || !sourceFile.path("size_bytes").isIntegralNumber()
                || !sourceFile.path("size_bytes").canConvertToLong()
                || sizeBytes < 1) {
            throw new ProcessorException(
                    "INVALID_MANIFEST",
                    "Source manifest has invalid shared metadata");
        }

        Path rawPath = workingDirectory.resolve(filename);
        Path checksumPath = workingDirectory.resolve(filename + ".sha256");
        artifactGateway.download(sourceDirectory + "/" + filename, rawPath);
        artifactGateway.download(
                sourceDirectory + "/" + filename + ".sha256",
                checksumPath);

        byte[] rawBytes = readBytes(rawPath);
        byte[] checksumBytes = readBytes(checksumPath);
        String actualSha256 = sha256(rawBytes);
        byte[] expectedSidecar = (
                sourceSha256 + "  " + filename + "\n")
                .getBytes(StandardCharsets.US_ASCII);
        if (rawBytes.length != sizeBytes
                || !actualSha256.equals(sourceSha256)
                || !MessageDigest.isEqual(expectedSidecar, checksumBytes)) {
            throw new ProcessorException(
                    "SOURCE_INTEGRITY_ERROR",
                    "Raw artifact integrity validation failed");
        }

        return new ProcessingContext(
                batchId,
                configuration,
                artifactGateway,
                workingDirectory,
                manifestBytes,
                manifest,
                new ProcessingContext.SourceArtifact(
                        filename,
                        sourceSha256,
                        sizeBytes,
                        rawBytes));
    }

    /**
     * Writes CSV, checksum, and sanitized manifest locally, then publishes all
     * three with the manifest renamed last as the readiness marker.
     */
    public static PublishedCsv publishSanitized(
            ProcessingContext context,
            String csvFilename,
            byte[] csvBytes,
            Map<String, Object> sanitizedManifest)
            throws ProcessorException {
        if (!SAFE_FILENAME.matcher(csvFilename).matches()) {
            throw new ProcessorException(
                    "INTERNAL_ERROR",
                    "Sanitized filename is unsafe");
        }
        String csvSha256 = sha256(csvBytes);
        Path csvPath = context.workingDirectory().resolve(csvFilename);
        Path checksumPath =
                context.workingDirectory().resolve(csvFilename + ".sha256");
        Path manifestPath =
                context.workingDirectory().resolve("sanitized-manifest.json");
        writeBytes(csvPath, csvBytes);
        writeBytes(
                checksumPath,
                (csvSha256 + "  " + csvFilename + "\n")
                        .getBytes(StandardCharsets.US_ASCII));
        writeBytes(
                manifestPath,
                StableJson.bytes(sanitizedManifest));

        LinkedHashMap<String, Path> publication = new LinkedHashMap<>();
        publication.put(csvFilename, csvPath);
        publication.put(csvFilename + ".sha256", checksumPath);
        publication.put("sanitized-manifest.json", manifestPath);
        context.artifactGateway().publish(
                "/csv/outgoing/" + context.batchId(),
                publication,
                "sanitized-manifest.json");
        return new PublishedCsv(csvFilename, csvSha256, csvBytes.length);
    }

    /**
     * Calculates lowercase SHA-256.
     */
    public static String sha256(byte[] content) {
        try {
            return HexFormat.of().formatHex(
                    MessageDigest.getInstance("SHA-256").digest(content));
        } catch (GeneralSecurityException exception) {
            throw new IllegalStateException(
                    "SHA-256 is unavailable",
                    exception);
        }
    }

    private static byte[] readBytes(Path path) throws ProcessorException {
        try {
            return Files.readAllBytes(path);
        } catch (IOException exception) {
            throw new ProcessorException(
                    "LOCAL_IO_ERROR",
                    "Cannot read temporary processing artifact",
                    exception);
        }
    }

    private static void writeBytes(Path path, byte[] content)
            throws ProcessorException {
        try {
            Files.write(path, content);
        } catch (IOException exception) {
            throw new ProcessorException(
                    "LOCAL_IO_ERROR",
                    "Cannot write temporary processing artifact",
                    exception);
        }
    }

    /**
     * Published sanitized CSV identity.
     */
    public record PublishedCsv(
            String filename,
            String sha256,
            long sizeBytes) {
    }
}
