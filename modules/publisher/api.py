import modules.authentication as authentication
import modules.cache as cache
import os
from modules.exceptions import (
    ApiResponseDecodeError,
    ApiResponseError,
    ApiResponseErrorList,
    MacaroonRefreshRequired
)


DASHBOARD_API = os.getenv(
    'DASHBOARD_API',
    'https://dashboard.snapcraft.io/dev/api/',
)

SNAP_PUB_METRICS_URL = ''.join([
    DASHBOARD_API,
    'snaps/metrics',
])
PUB_METRICS_QUERY_HEADERS = {
    'Content-Type': 'application/json'
}

ACCOUNT_URL = ''.join([
    DASHBOARD_API,
    'account',
])

AGREEMENT_URL = ''.join([
    DASHBOARD_API,
    'agreement/'
])

METADATA_QUERY_URL = ''.join([
    DASHBOARD_API,
    'snaps/{snap_id}/metadata',
])

STATUS_QUERY_URL = ''.join([
    DASHBOARD_API,
    'snaps/{snap_id}/status',
])

SCREENSHOTS_QUERY_URL = ''.join([
    DASHBOARD_API,
    'snaps/{snap_id}/binary-metadata'
])

SNAP_INFO_URL = ''.join([
    DASHBOARD_API,
    'snaps/info/{snap_name}',
])


def process_response(response):
    try:
        body = response.json()
    except ValueError as decode_error:
        api_error_exception = ApiResponseDecodeError(
            'JSON decoding failed: {}'.format(decode_error),
        )
        raise api_error_exception

    if not response.ok:
        if 'error_list' in body:
            api_error_exception = ApiResponseErrorList(
                'The api returned a list of errors',
                response.status_code,
                body['error_list']
            )
            raise api_error_exception
        else:
            raise ApiResponseError(
                'Unknown error from api',
                response.status_code
            )

    return body


def get_authorization_header(session):
    authorization = authentication.get_authorization_header(
        session['macaroon_root'],
        session['macaroon_discharge']
    )

    return {
        'Authorization': authorization
    }


def get_account(session):
    authorization = authentication.get_authorization_header(
        session['macaroon_root'],
        session['macaroon_discharge']
    )

    headers = {
        'X-Ubuntu-Series': '16',
        'X-Ubuntu-Architecture': 'amd64',
        'Authorization': authorization
    }

    response = cache.get(
        url=ACCOUNT_URL,
        method='GET',
        headers=headers
    )

    if authentication.is_macaroon_expired(response.headers):
        raise MacaroonRefreshRequired()

    return response.json()


def get_agreement(session):
    headers = get_authorization_header(session)

    agreement_response = cache.get(
        AGREEMENT_URL,
        headers
    )

    if authentication.is_macaroon_expired(agreement_response.headers):
        raise MacaroonRefreshRequired()

    return agreement_response.json()


def post_agreement(session, agreed):
    headers = get_authorization_header(session)

    json = {
        'latest_tos_accepted': agreed
    }
    agreement_response = cache.get(
        AGREEMENT_URL,
        headers,
        json
    )

    if authentication.is_macaroon_expired(agreement_response.headers):
        raise MacaroonRefreshRequired()

    return agreement_response.json()


def post_username(session, username):
    headers = get_authorization_header(session)
    json = {
        'short_namespace': username
    }
    username_response = cache.get(
        url=ACCOUNT_URL,
        headers=headers,
        json=json,
        method='PATCH'
    )

    if authentication.is_macaroon_expired(username_response.headers):
        raise MacaroonRefreshRequired()

    if username_response.status_code == 204:
        return {}
    else:
        return username_response.json()


def get_publisher_metrics(session, json):
    authed_metrics_headers = PUB_METRICS_QUERY_HEADERS.copy()
    auth_header = get_authorization_header(session)['Authorization']
    authed_metrics_headers['Authorization'] = auth_header

    metrics_response = cache.get(
        SNAP_PUB_METRICS_URL,
        headers=authed_metrics_headers,
        json=json
    )

    if authentication.is_macaroon_expired(metrics_response.headers):
        raise MacaroonRefreshRequired()

    return metrics_response.json()


def get_snap_info(snap_name, session):
    response = cache.get(
        SNAP_INFO_URL.format(snap_name=snap_name),
        headers=get_authorization_header(session)
    )

    if authentication.is_macaroon_expired(response.headers):
        raise MacaroonRefreshRequired()

    return process_response(response)


def get_snap_id(snap_name, session):
    snap_info = get_snap_info(snap_name, session)

    return snap_info['snap_id']


def snap_metadata(snap_id, session, json=None):
    method = "PUT" if json is not None else None

    metadata_response = cache.get(
        METADATA_QUERY_URL.format(snap_id=snap_id),
        headers=get_authorization_header(session),
        json=json,
        method=method
    )

    if authentication.is_macaroon_expired(metadata_response.headers):
        raise MacaroonRefreshRequired()

    return metadata_response.json()


def get_snap_status(snap_id, session):
    status_response = cache.get(
        STATUS_QUERY_URL.format(snap_id=snap_id),
        headers=get_authorization_header(session)
    )

    if authentication.is_macaroon_expired(status_response.headers):
        raise MacaroonRefreshRequired()

    return status_response.json()


def snap_screenshots(snap_id, session, data=None, files=None):
    method = None
    files_array = None
    headers = get_authorization_header(session)
    headers['Accept'] = 'application/json'

    if data:
        method = 'PUT'

        files_array = []
        if files:
            for f in files:
                files_array.append(
                    (f.filename, (f.filename, f.stream, f.mimetype))
                )
        else:
            # API requires a multipart request, but we have no files to push
            # https://github.com/requests/requests/issues/1081
            files_array = {'info': ('', data['info'])}
            data = None

    screenshot_response = cache.get(
        SCREENSHOTS_QUERY_URL.format(snap_id=snap_id),
        headers=headers,
        data=data,
        method=method,
        files=files_array
    )

    if authentication.is_macaroon_expired(screenshot_response.headers):
        raise MacaroonRefreshRequired()

    return screenshot_response.json()
