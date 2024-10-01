# import pytest
# from lambda_hundler import execute_compound_investment

# # Example test case for execute_compound_investment
# def test_execute_compound_investment():
#     result = execute_compound_investment()
#     assert result is not None
#     # You can add assertions based on expected behavior

# from unittest.mock import patch

# @patch('lambda_hundler.oandapyV20.API')
# def test_execute_compound_investment(mock_api):
#     mock_api.return_value.some_function.return_value = 'mocked_response'
#     result = execute_compound_investment()
#     assert result == 'expected_result'