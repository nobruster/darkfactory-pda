package com.northwindpay.legacy.core;

import java.nio.charset.StandardCharsets;
import java.security.GeneralSecurityException;
import java.security.MessageDigest;
import java.util.Collection;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.Map;
import java.util.Set;

/**
 * Clear-value-free matcher used to enforce diagnostic privacy.
 *
 * <p>Only SHA-256 fingerprints and source-value lengths are retained. Result
 * construction scans every scalar or collection field for any restricted
 * value before serialization.
 */
public final class DiagnosticPrivacy {
    private static final DiagnosticPrivacy EMPTY =
            new DiagnosticPrivacy(Map.of());
    private final Map<Integer, Set<String>> fingerprintsByLength;

    private DiagnosticPrivacy(
            Map<Integer, Set<String>> fingerprintsByLength) {
        this.fingerprintsByLength = fingerprintsByLength;
    }

    /**
     * Builds a matcher without retaining any supplied clear value.
     */
    public static DiagnosticPrivacy fromRestrictedValues(
            Collection<String> restrictedValues) {
        if (restrictedValues == null || restrictedValues.isEmpty()) {
            return EMPTY;
        }
        Map<Integer, Set<String>> mutable = new LinkedHashMap<>();
        for (String value : restrictedValues) {
            if (value == null || value.isEmpty()) {
                continue;
            }
            mutable.computeIfAbsent(
                    value.length(),
                    ignored -> new LinkedHashSet<>())
                    .add(fingerprint(value));
        }
        if (mutable.isEmpty()) {
            return EMPTY;
        }
        Map<Integer, Set<String>> immutable = new LinkedHashMap<>();
        for (Map.Entry<Integer, Set<String>> entry
                : mutable.entrySet()) {
            immutable.put(
                    entry.getKey(),
                    Collections.unmodifiableSet(
                            new LinkedHashSet<>(entry.getValue())));
        }
        return new DiagnosticPrivacy(
                Collections.unmodifiableMap(immutable));
    }

    /**
     * Returns null when the value contains any restricted clear value.
     */
    public String redact(String value) {
        return containsRestrictedValue(value) ? null : value;
    }

    Map<String, Object> redactResult(Map<String, Object> result) {
        if (fingerprintsByLength.isEmpty()) {
            return result;
        }
        LinkedHashMap<String, Object> safe = new LinkedHashMap<>();
        for (Map.Entry<String, Object> entry : result.entrySet()) {
            safe.put(
                    entry.getKey(),
                    containsRestrictedValue(entry.getValue())
                            ? null
                            : entry.getValue());
        }
        return safe;
    }

    boolean containsRestrictedValue(Object value) {
        if (value == null) {
            return false;
        }
        if (value instanceof Iterable<?> iterable) {
            for (Object item : iterable) {
                if (containsRestrictedValue(item)) {
                    return true;
                }
            }
            return false;
        }
        String rendered = value.toString();
        for (Map.Entry<Integer, Set<String>> entry
                : fingerprintsByLength.entrySet()) {
            int length = entry.getKey();
            if (rendered.length() < length) {
                continue;
            }
            for (int start = 0;
                    start <= rendered.length() - length;
                    start++) {
                String candidate =
                        rendered.substring(start, start + length);
                if (entry.getValue().contains(
                        fingerprint(candidate))) {
                    return true;
                }
            }
        }
        return false;
    }

    private static String fingerprint(String value) {
        try {
            return java.util.HexFormat.of().formatHex(
                    MessageDigest.getInstance("SHA-256").digest(
                            value.getBytes(StandardCharsets.UTF_8)));
        } catch (GeneralSecurityException exception) {
            throw new IllegalStateException(
                    "SHA-256 is unavailable",
                    exception);
        }
    }
}
