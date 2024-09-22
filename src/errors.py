from typing import Any, Callable
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from fastapi import FastAPI, status
from sqlalchemy.exc import SQLAlchemyError


class BeehaivException(Exception):
    """This is the base class for all Beehaiv errors."""

    pass


# Authentication and Authorization Errors
class InvalidToken(BeehaivException):
    """User has provided an invalid or expired token."""

    pass


class RevokedToken(BeehaivException):
    """User has provided a token that has been revoked."""

    pass


class AccessTokenRequired(BeehaivException):
    """User has provided a refresh token when an access token is needed."""

    pass


class RefreshTokenRequired(BeehaivException):
    """User has provided an access token when a refresh token is needed."""

    pass


# User-related Errors
class UserAlreadyExists(BeehaivException):
    """User has provided an email for a user who exists during sign up."""

    pass


class UserNotFound(BeehaivException):
    """User not found."""

    pass

class UserBlocked(BeehaivException):
    """This user has been blocked due to suspicious attempts to login from a new ip address"""

    pass


class InvalidCredentials(BeehaivException):
    """User has provided wrong email or password during log in."""

    pass


class InsufficientPermission(BeehaivException):
    """User does not have the necessary permissions to perform an action."""

    pass


class AccountNotVerified(BeehaivException):
    """Account not yet verified."""

    pass


# Transaction Errors
class TransactionNotFound(BeehaivException):
    """Transaction not found."""

    pass


class InvalidTransactionPin(BeehaivException):
    """You have inputted a wrong transfer pin."""

    pass


class InvalidTransactionAmount(BeehaivException):
    """Invalid transaction amount specified."""

    pass


# Blog Post Errors
class BlogPostNotFound(BeehaivException):
    """Blog post not found."""

    pass


class BlogPostAlreadyExists(BeehaivException):
    """Blog post with the given title or slug already exists."""

    pass


# Debit Card Errors
class DebitCardNotFound(BeehaivException):
    """Debit card not found."""

    pass


class CardLimitExceeded(BeehaivException):
    """Debit card transaction exceeds the allowed limit."""

    pass


# Bank Account Errors
class BankAccountNotFound(BeehaivException):
    """Bank account not found."""

    pass


class InsufficientFunds(BeehaivException):
    """Bank account has insufficient funds."""

    pass


# Loan Errors
class LoanNotFound(BeehaivException):
    """Loan not found."""

    pass


class LoanAlreadyExists(BeehaivException):
    """Loan with the given identifier already exists."""

    pass


class LoanRepaymentError(BeehaivException):
    """Error processing loan repayment."""

    pass


# Business Registration Errors
class BusinessRegistrationFailed(BeehaivException):
    """Business registration failed due to invalid or missing information."""

    pass


class BusinessNotFound(BeehaivException):
    """Business not found."""

    pass


class BusinessAlreadyExists(BeehaivException):
    """Business with the given name or registration number already exists."""

    pass


# Business Number Errors
class InvalidBusinessNumber(BeehaivException):
    """Invalid business number provided."""

    pass


class BusinessNumberNotFound(BeehaivException):
    """Business number not found in records."""

    pass


class BusinessNumberAlreadyExists(BeehaivException):
    """Business number already associated with another business."""

    pass


# General Business Errors
class UnauthorizedBusinessAccess(BeehaivException):
    """Unauthorized access attempt to business data."""

    pass


def create_exception_handler(
    status_code: int, initial_detail: Any
) -> Callable[[Request, Exception], JSONResponse]:
    async def exception_handler(request: Request, exc: BeehaivException):
        return JSONResponse(content=initial_detail, status_code=status_code)

    return exception_handler


def register_all_errors(app: FastAPI):
    # User-related Error Handlers
    app.add_exception_handler(
        UserAlreadyExists,
        create_exception_handler(
            status_code=status.HTTP_403_FORBIDDEN,
            initial_detail={
                "message": "User with email already exists",
                "error_code": "user_exists",
            },
        ),
    )

    app.add_exception_handler(
        UserNotFound,
        create_exception_handler(
            status_code=status.HTTP_404_NOT_FOUND,
            initial_detail={
                "message": "User not found",
                "error_code": "user_not_found",
            },
        ),
    )

    app.add_exception_handler(
        UserBlocked,
        create_exception_handler(
            status_code=status.HTTP_423_LOCKED,
            initial_detail=(
                "message": "User is restricted",
                "error_code": "user_is_restricted",
            )
        )
    )

    app.add_exception_handler(
        InvalidCredentials,
        create_exception_handler(
            status_code=status.HTTP_400_BAD_REQUEST,
            initial_detail={
                "message": "Invalid Email Or Password",
                "error_code": "invalid_email_or_password",
            },
        ),
    )

    # Token-related Error Handlers
    app.add_exception_handler(
        InvalidToken,
        create_exception_handler(
            status_code=status.HTTP_401_UNAUTHORIZED,
            initial_detail={
                "message": "Token is invalid or expired",
                "resolution": "Please get a new token",
                "error_code": "invalid_token",
            },
        ),
    )

    app.add_exception_handler(
        RevokedToken,
        create_exception_handler(
            status_code=status.HTTP_401_UNAUTHORIZED,
            initial_detail={
                "message": "Token is invalid or has been revoked",
                "resolution": "Please get a new token",
                "error_code": "token_revoked",
            },
        ),
    )

    app.add_exception_handler(
        AccessTokenRequired,
        create_exception_handler(
            status_code=status.HTTP_401_UNAUTHORIZED,
            initial_detail={
                "message": "Please provide a valid access token",
                "resolution": "Please get an access token",
                "error_code": "access_token_required",
            },
        ),
    )

    app.add_exception_handler(
        RefreshTokenRequired,
        create_exception_handler(
            status_code=status.HTTP_403_FORBIDDEN,
            initial_detail={
                "message": "Please provide a valid refresh token",
                "resolution": "Please get a refresh token",
                "error_code": "refresh_token_required",
            },
        ),
    )

    app.add_exception_handler(
        InsufficientPermission,
        create_exception_handler(
            status_code=status.HTTP_401_UNAUTHORIZED,
            initial_detail={
                "message": "You do not have enough permissions to perform this action",
                "error_code": "insufficient_permissions",
            },
        ),
    )

    # Transaction Error Handlers
    app.add_exception_handler(
        TransactionNotFound,
        create_exception_handler(
            status_code=status.HTTP_404_NOT_FOUND,
            initial_detail={
                "message": "Transaction not found",
                "error_code": "transaction_not_found",
            },
        ),
    )

    app.add_exception_handler(
        InvalidTransactionPin,
        create_exception_handler(
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
            initial_detail={
                "message": "Transaction pin incorrect",
                "error_code": "transaction_pin_incorrect",
            },
        ),
    )

    app.add_exception_handler(
        InvalidTransactionAmount,
        create_exception_handler(
            status_code=status.HTTP_400_BAD_REQUEST,
            initial_detail={
                "message": "Invalid transaction amount specified",
                "error_code": "invalid_transaction_amount",
            },
        ),
    )

    # Blog Post Error Handlers
    app.add_exception_handler(
        BlogPostNotFound,
        create_exception_handler(
            status_code=status.HTTP_404_NOT_FOUND,
            initial_detail={
                "message": "Blog post not found",
                "error_code": "blog_post_not_found",
            },
        ),
    )

    app.add_exception_handler(
        BlogPostAlreadyExists,
        create_exception_handler(
            status_code=status.HTTP_403_FORBIDDEN,
            initial_detail={
                "message": "Blog post already exists",
                "error_code": "blog_post_exists",
            },
        ),
    )

    # Debit Card Error Handlers
    app.add_exception_handler(
        DebitCardNotFound,
        create_exception_handler(
            status_code=status.HTTP_404_NOT_FOUND,
            initial_detail={
                "message": "Debit card not found",
                "error_code": "debit_card_not_found",
            },
        ),
    )

    app.add_exception_handler(
        CardLimitExceeded,
        create_exception_handler(
            status_code=status.HTTP_400_BAD_REQUEST,
            initial_detail={
                "message": "Card transaction exceeds the allowed limit",
                "error_code": "card_limit_exceeded",
            },
        ),
    )

    # Bank Account Error Handlers
    app.add_exception_handler(
        BankAccountNotFound,
        create_exception_handler(
            status_code=status.HTTP_404_NOT_FOUND,
            initial_detail={
                "message": "Bank account not found",
                "error_code": "bank_account_not_found",
            },
        ),
    )

    app.add_exception_handler(
        InsufficientFunds,
        create_exception_handler(
            status_code=status.HTTP_400_BAD_REQUEST,
            initial_detail={
                "message": "Insufficient funds in the bank account",
                "error_code": "insufficient_funds",
            },
        ),
    )

    # Loan Error Handlers
    app.add_exception_handler(
        LoanNotFound,
        create_exception_handler(
            status_code=status.HTTP_404_NOT_FOUND,
            initial_detail={
                "message": "Loan not found",
                "error_code": "loan_not_found",
            },
        ),
    )

    app.add_exception_handler(
        LoanAlreadyExists,
        create_exception_handler(
            status_code=status.HTTP_403_FORBIDDEN,
            initial_detail={
                "message": "Loan already exists",
                "error_code": "loan_exists",
            },
        ),
    )

    app.add_exception_handler(
        LoanRepaymentError,
        create_exception_handler(
            status_code=status.HTTP_400_BAD_REQUEST,
            initial_detail={
                "message": "Error processing loan repayment",
                "error_code": "loan_repayment_error",
            },
        ),
    )

    # Business Registration Error Handlers
    app.add_exception_handler(
        BusinessRegistrationFailed,
        create_exception_handler(
            status_code=status.HTTP_400_BAD_REQUEST,
            initial_detail={
                "message": "Business registration failed",
                "error_code": "business_registration_failed",
            },
        ),
    )

    app.add_exception_handler(
        BusinessNotFound,
        create_exception_handler(
            status_code=status.HTTP_404_NOT_FOUND,
            initial_detail={
                "message": "Business not found",
                "error_code": "business_not_found",
            },
        ),
    )

    app.add_exception_handler(
        BusinessAlreadyExists,
        create_exception_handler(
            status_code=status.HTTP_403_FORBIDDEN,
            initial_detail={
                "message": "Business already exists",
                "error_code": "business_exists",
            },
        ),
    )

    # Business Number Error Handlers
    app.add_exception_handler(
        InvalidBusinessNumber,
        create_exception_handler(
            status_code=status.HTTP_400_BAD_REQUEST,
            initial_detail={
                "message": "Invalid business number provided",
                "error_code": "invalid_business_number",
            },
        ),
    )

    app.add_exception_handler(
        BusinessNumberNotFound,
        create_exception_handler(
            status_code=status.HTTP_404_NOT_FOUND,
            initial_detail={
                "message": "Business number not found",
                "error_code": "business_number_not_found",
            },
        ),
    )

    app.add_exception_handler(
        BusinessNumberAlreadyExists,
        create_exception_handler(
            status_code=status.HTTP_403_FORBIDDEN,
            initial_detail={
                "message": "Business number already associated with another business",
                "error_code": "business_number_exists",
            },
        ),
    )

    # General Business Error Handlers
    app.add_exception_handler(
        UnauthorizedBusinessAccess,
        create_exception_handler(
            status_code=status.HTTP_401_UNAUTHORIZED,
            initial_detail={
                "message": "Unauthorized access to business data",
                "error_code": "unauthorized_business_access",
            },
        ),
    )

    app.add_exception_handler(
        AccountNotVerified,
        create_exception_handler(
            status_code=status.HTTP_403_FORBIDDEN,
            initial_detail={
                "message": "Account not verified",
                "error_code": "account_not_verified",
                "resolution": "Please check your email for verification details",
            },
        ),
    )

    @app.exception_handler(500)
    async def internal_server_error(request: Request, exc: Exception):
        return JSONResponse(
            content={
                "message": "Oops! Something went wrong",
                "error_code": "server_error",
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    @app.exception_handler(SQLAlchemyError)
    async def database_error(request: Request, exc: SQLAlchemyError):
        print(str(exc))
        return JSONResponse(
            content={
                "message": "Database error occurred",
                "error_code": "database_error",
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
