/**
 * Merchant-chargeback conversion for legacy Type 06.
 *
 * <p>Source parsing keeps contract HALF_UP. Sanitized CSV rendering plants
 * HALF_EVEN so a 1.005 row can MATCHED at a different cent than the contract.
 */
package com.northwindpay.legacy.type06;
