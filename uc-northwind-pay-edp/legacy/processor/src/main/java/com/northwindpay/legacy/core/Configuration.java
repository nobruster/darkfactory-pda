package com.northwindpay.legacy.core;

import java.nio.file.Path;
import java.util.Map;

/**
 * Immutable runtime settings shared by every legacy file processor.
 *
 * <p>Connection settings are shared. Secret keys stay separate and are
 * validated by the processor that owns their data domain, so Type 02 never
 * falls back to the Type 01 PAN tokenization key.
 *
 * @param host SFTP host
 * @param port SFTP port
 * @param username processor SFTP username
 * @param password processor SFTP password
 * @param knownHosts pinned SSH known-hosts file
 * @param tokenizationKey Type 01 PAN HMAC key
 * @param documentTokenKey Type 02 document HMAC key
 * @param paymentReferenceKey Type 03 payment-reference HMAC key
 * @param partyTokenKey Type 03 party HMAC key
 * @param accountTokenKey Type 03 account HMAC key
 * @param tedAccountTokenKey Type 04 payer/beneficiary account HMAC key
 */
public record Configuration(
        String host,
        int port,
        String username,
        String password,
        Path knownHosts,
        String tokenizationKey,
        String documentTokenKey,
        String paymentReferenceKey,
        String partyTokenKey,
        String accountTokenKey,
        String tedAccountTokenKey) {

    /**
     * Backward-compatible constructor for the Type 03 settings introduced
     * before the dedicated Type 04 TED account domain.
     *
     * @param host SFTP host
     * @param port SFTP port
     * @param username processor SFTP username
     * @param password processor SFTP password
     * @param knownHosts pinned SSH known-hosts file
     * @param tokenizationKey Type 01 PAN HMAC key
     * @param documentTokenKey Type 02 document HMAC key
     * @param paymentReferenceKey Type 03 payment-reference HMAC key
     * @param partyTokenKey Type 03 party HMAC key
     * @param accountTokenKey Type 03 account HMAC key
     */
    public Configuration(
            String host,
            int port,
            String username,
            String password,
            Path knownHosts,
            String tokenizationKey,
            String documentTokenKey,
            String paymentReferenceKey,
            String partyTokenKey,
            String accountTokenKey) {
        this(
                host,
                port,
                username,
                password,
                knownHosts,
                tokenizationKey,
                documentTokenKey,
                paymentReferenceKey,
                partyTokenKey,
                accountTokenKey,
                null);
    }

    /**
     * Backward-compatible constructor for the original Type 01/02 settings.
     *
     * @param host SFTP host
     * @param port SFTP port
     * @param username processor SFTP username
     * @param password processor SFTP password
     * @param knownHosts pinned SSH known-hosts file
     * @param tokenizationKey Type 01 PAN HMAC key
     * @param documentTokenKey Type 02 document HMAC key
     */
    public Configuration(
            String host,
            int port,
            String username,
            String password,
            Path knownHosts,
            String tokenizationKey,
            String documentTokenKey) {
        this(
                host,
                port,
                username,
                password,
                knownHosts,
                tokenizationKey,
                documentTokenKey,
                null,
                null,
                null,
                null);
    }

    /**
     * Returns only non-secret connection identity for safe diagnostics.
     */
    @Override
    public String toString() {
        return "Configuration[host="
                + host
                + ", port="
                + port
                + ", username="
                + username
                + ", knownHosts="
                + knownHosts
                + ", tokenizationKey=<redacted>"
                + ", documentTokenKey=<redacted>"
                + ", paymentReferenceKey=<redacted>"
                + ", partyTokenKey=<redacted>"
                + ", accountTokenKey=<redacted>"
                + ", tedAccountTokenKey=<redacted>]";
    }

    /**
     * Loads validated settings without serializing any secret.
     *
     * @param environment process environment
     * @return validated runtime configuration
     * @throws ProcessorException when a required shared setting is absent
     */
    public static Configuration fromEnvironment(Map<String, String> environment)
            throws ProcessorException {
        return new Configuration(
                required(environment, "SFTP_HOST"),
                parsePort(required(environment, "SFTP_PORT")),
                required(environment, "SFTP_PROCESSOR_USER"),
                required(environment, "SFTP_PROCESSOR_PASSWORD"),
                Path.of(required(environment, "SFTP_KNOWN_HOSTS")),
                environment.get("NWP_TOKENIZATION_KEY"),
                environment.get("NWP_DOCUMENT_TOKEN_KEY"),
                environment.get("NWP_PAYMENT_REFERENCE_KEY"),
                environment.get("NWP_PARTY_TOKEN_KEY"),
                environment.get("NWP_ACCOUNT_TOKEN_KEY"),
                environment.get("NWP_TED_ACCOUNT_TOKEN_KEY"));
    }

    private static String required(Map<String, String> environment, String name)
            throws ProcessorException {
        String value = environment.get(name);
        if (value == null || value.isBlank()) {
            throw new ProcessorException(
                    "CONFIGURATION_ERROR",
                    "Missing required environment setting: " + name);
        }
        return value;
    }

    private static int parsePort(String value) throws ProcessorException {
        try {
            int port = Integer.parseInt(value);
            if (port < 1 || port > 65535) {
                throw new NumberFormatException("out of range");
            }
            return port;
        } catch (NumberFormatException exception) {
            throw new ProcessorException("CONFIGURATION_ERROR", "SFTP_PORT is invalid");
        }
    }
}
