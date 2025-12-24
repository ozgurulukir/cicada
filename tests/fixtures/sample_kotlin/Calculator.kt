/**
 * A simple calculator that performs basic arithmetic operations.
 *
 * This module provides basic arithmetic operations through the Calculator class.
 */
class Calculator(
    /** The current value stored in the calculator. */
    private var value: Int = 0
) {
    /**
     * Add two numbers and return the result.
     *
     * @param x First number
     * @param y Second number
     * @return Sum of x and y
     */
    fun add(x: Int, y: Int): Int {
        return x + y
    }

    /**
     * Multiply two numbers and return the result.
     *
     * @param x First number
     * @param y Second number
     * @return Product of x and y
     */
    fun multiply(x: Int, y: Int): Int {
        return x * y
    }

    /**
     * Divide x by y and return the result.
     *
     * @param x Numerator
     * @param y Denominator
     * @return Result of division
     */
    fun divide(x: Double, y: Double): Double {
        return x / y
    }

    /**
     * Private method (should be marked as private in index).
     */
    private fun privateMethod(): String {
        return "private"
    }

    /**
     * Calculate a complex expression using multiple operations.
     *
     * @param x First operand
     * @param y Second operand
     * @param z Third operand
     * @return Result of (x + y) * z
     */
    fun calculateExpression(x: Int, y: Int, z: Int): Int {
        val sumResult = add(x, y)
        return multiply(sumResult, z)
    }
}

/**
 * Top-level helper function to process data.
 *
 * @param data List of items
 * @return Size of the list
 */
fun helperFunction(data: List<Int>): Int {
    return data.size
}

/**
 * Private top-level function (internal visibility).
 */
private fun privateFunction() {
    // Private implementation
}
