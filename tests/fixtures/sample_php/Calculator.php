<?php

declare(strict_types=1);

/**
 * A simple calculator that performs basic arithmetic operations.
 *
 * This module provides basic arithmetic operations through the Calculator class.
 */
class Calculator
{
    /**
     * The current value stored in the calculator.
     */
    private int $value;

    /**
     * Initialize calculator with an optional starting value.
     *
     * @param int $initialValue The starting value (default: 0)
     */
    public function __construct(int $initialValue = 0)
    {
        $this->value = $initialValue;
    }

    /**
     * Add two numbers and return the result.
     *
     * @param int $x First number
     * @param int $y Second number
     * @return int Sum of x and y
     */
    public function add(int $x, int $y): int
    {
        return $x + $y;
    }

    /**
     * Multiply two numbers and return the result.
     *
     * @param int $x First number
     * @param int $y Second number
     * @return int Product of x and y
     */
    public function multiply(int $x, int $y): int
    {
        return $x * $y;
    }

    /**
     * Divide x by y and return the result.
     *
     * @param float $x Numerator
     * @param float $y Denominator
     * @return float Result of division
     */
    public function divide(float $x, float $y): float
    {
        return $x / $y;
    }

    /**
     * Private method (should be marked as private in index).
     *
     * @return string
     */
    private function privateMethod(): string
    {
        return 'private';
    }

    /**
     * Calculate a complex expression using multiple operations.
     *
     * @param int $x First operand
     * @param int $y Second operand
     * @param int $z Third operand
     * @return int Result of (x + y) * z
     */
    public function calculateExpression(int $x, int $y, int $z): int
    {
        $sumResult = $this->add($x, $y);
        return $this->multiply($sumResult, $z);
    }
}

/**
 * Top-level helper function to process data.
 *
 * @param array<int> $data Array of items
 * @return int Length of the array
 */
function helperFunction(array $data): int
{
    return count($data);
}

/**
 * Private function (not exported in class context).
 */
function _privateFunction(): void
{
    // Private implementation
}
