package com.northwindpay.legacy.core;

/**
 * A bounded parser/converter for one registered legacy file contract.
 */
public interface BatchProcessor {
    /**
     * Two-digit manifest type number.
     */
    String typeNumber();

    /**
     * Header and manifest type code.
     */
    String typeCode();

    /**
     * Supported source layout version.
     */
    String layoutVersion();

    /**
     * Validates, converts, and publishes a previously integrity-checked source.
     */
    ProcessorResult process(ProcessingContext context)
            throws ProcessorException;
}
