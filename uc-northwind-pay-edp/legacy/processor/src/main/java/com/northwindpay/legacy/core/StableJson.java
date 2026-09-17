package com.northwindpay.legacy.core;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.StreamReadFeature;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.MapperFeature;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.fasterxml.jackson.databind.json.JsonMapper;

import java.io.IOException;
import java.nio.charset.StandardCharsets;

/**
 * Deterministic JSON codec used for manifests and the one-line process result.
 */
public final class StableJson {
    private static final ObjectMapper MAPPER = JsonMapper.builder()
            .enable(StreamReadFeature.STRICT_DUPLICATE_DETECTION)
            .enable(MapperFeature.SORT_PROPERTIES_ALPHABETICALLY)
            .enable(SerializationFeature.ORDER_MAP_ENTRIES_BY_KEYS)
            .enable(SerializationFeature.INDENT_OUTPUT)
            .build();

    private StableJson() {
    }

    public static JsonNode parse(byte[] content) throws ProcessorException {
        try {
            return MAPPER.readTree(content);
        } catch (IOException exception) {
            throw new ProcessorException("INVALID_MANIFEST", "Manifest is not valid JSON", exception);
        }
    }

    public static byte[] bytes(Object value) throws ProcessorException {
        try {
            return (MAPPER.writeValueAsString(value) + "\n").getBytes(StandardCharsets.UTF_8);
        } catch (JsonProcessingException exception) {
            throw new ProcessorException("INTERNAL_ERROR", "Cannot serialize safe processing metadata", exception);
        }
    }

    public static String line(Object value) throws ProcessorException {
        try {
            return MAPPER.writer()
                    .without(SerializationFeature.INDENT_OUTPUT)
                    .writeValueAsString(value);
        } catch (JsonProcessingException exception) {
            throw new ProcessorException("INTERNAL_ERROR", "Cannot serialize safe processing result", exception);
        }
    }
}
