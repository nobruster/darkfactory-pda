package com.northwindpay.legacy.core;

import com.fasterxml.jackson.databind.JsonNode;

import java.nio.file.Path;
import java.util.Collection;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Explicit typed registry and source-manifest-based processor dispatcher.
 */
public final class ProcessorDispatcher {
    private final Map<String, BatchProcessor> processors;

    /**
     * Creates a closed registry, rejecting duplicate type numbers.
     */
    public ProcessorDispatcher(Collection<? extends BatchProcessor> values) {
        LinkedHashMap<String, BatchProcessor> registered =
                new LinkedHashMap<>();
        for (BatchProcessor processor : values) {
            if (registered.putIfAbsent(
                    processor.typeNumber(),
                    processor) != null) {
                throw new IllegalArgumentException(
                        "Duplicate processor type registration");
            }
        }
        this.processors = Map.copyOf(registered);
    }

    /**
     * Acquires one source bundle and dispatches by its manifest type.
     *
     * @param expectedType optional CLI assertion such as {@code 02}
     */
    public ProcessorResult dispatch(
            String batchId,
            String expectedType,
            Configuration configuration,
            ArtifactGateway artifactGateway,
            Path workingDirectory) throws ProcessorException {
        ProcessingContext context = ArtifactIO.acquire(
                batchId,
                configuration,
                artifactGateway,
                workingDirectory);
        JsonNode fileType = context.sourceManifest().path("file_type");
        String actualType = fileType.path("number").asText();
        if (expectedType != null && !expectedType.equals(actualType)) {
            throw new ProcessorException(
                    "PROCESSOR_SELECTION_MISMATCH",
                    "Requested processor type does not match source manifest")
                    .forType(actualType);
        }
        BatchProcessor processor = processors.get(actualType);
        if (processor == null) {
            throw new ProcessorException(
                    "UNSUPPORTED_FILE_TYPE",
                    "No processor is registered for source manifest type")
                    .forType(actualType);
        }
        if (!processor.typeCode().equals(
                    fileType.path("code").asText())
                || !processor.layoutVersion().equals(
                    fileType.path("layout_version").asText())
                || !fileType.path("code").isTextual()
                || !fileType.path("layout_version").isTextual()
                || !fileType.path("contract_version").isIntegralNumber()
                || fileType.path("contract_version").intValue() != 1) {
            throw new ProcessorException(
                    "PROCESSOR_SELECTION_MISMATCH",
                    "Manifest identity does not match registered processor")
                    .forType(actualType);
        }
        try {
            return processor.process(context);
        } catch (ProcessorException exception) {
            throw exception.forType(actualType);
        }
    }
}
