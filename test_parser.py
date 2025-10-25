"""
Unit tests for the Elixir parser.
"""

from parser import ElixirParser


def test_simple_module():
    """Test parsing a simple module with one function."""
    parser = ElixirParser()
    result = parser.parse_file('test_fixtures/sample.ex')

    assert result is not None
    assert len(result) == 1

    module = result[0]
    assert module['module'] == 'Test'
    assert module['line'] == 1
    assert len(module['functions']) == 5


def test_function_extraction():
    """Test that functions are correctly extracted."""
    parser = ElixirParser()
    result = parser.parse_file('test_fixtures/sample.ex')

    functions = result[0]['functions']

    # Check hello/1
    hello = next(f for f in functions if f['name'] == 'hello')
    assert hello['arity'] == 1
    assert hello['full_name'] == 'hello/1'
    assert hello['type'] == 'def'
    assert hello['line'] == 6

    # Check private_func/0
    private = next(f for f in functions if f['name'] == 'private_func')
    assert private['arity'] == 0
    assert private['full_name'] == 'private_func/0'
    assert private['type'] == 'defp'
    assert private['line'] == 10

    # Check multi_arity/3
    multi = next(f for f in functions if f['name'] == 'multi_arity')
    assert multi['arity'] == 3
    assert multi['full_name'] == 'multi_arity/3'
    assert multi['type'] == 'def'

    # Check another_private/2
    another = next(f for f in functions if f['name'] == 'another_private')
    assert another['arity'] == 2
    assert another['type'] == 'defp'


def test_no_params_function():
    """Test function with no parameters."""
    parser = ElixirParser()
    result = parser.parse_file('test_fixtures/sample.ex')

    functions = result[0]['functions']
    no_params = next(f for f in functions if f['name'] == 'no_params')

    assert no_params['arity'] == 0
    assert no_params['full_name'] == 'no_params/0'


if __name__ == '__main__':
    print("Running parser tests...")

    try:
        test_simple_module()
        print("✓ test_simple_module passed")

        test_function_extraction()
        print("✓ test_function_extraction passed")

        test_no_params_function()
        print("✓ test_no_params_function passed")

        print("\nAll tests passed!")
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
