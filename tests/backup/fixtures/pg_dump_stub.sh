#!/usr/bin/env bash
# Deterministic pg_dump stub used ONLY for failure-injection tests.
# Behaviour is selected by FAKE_PG_DUMP_MODE; it never touches a database.
set -u
case "${FAKE_PG_DUMP_MODE:-invalid}" in
  fail)
    echo "pg_dump: error: connection to server failed" >&2
    exit 1
    ;;
  empty)
    exit 0
    ;;
  invalid)
    printf '%s\n' '-- this is not a real PostgreSQL dump'
    exit 0
    ;;
  ddl)
    printf '%s\n' \
      '--' '-- PostgreSQL database dump' '--' \
      'DROP DATABASE IF EXISTS autoflow;' \
      'CREATE DATABASE autoflow;' \
      '\connect autoflow' \
      '-- PostgreSQL database dump complete' '--'
    exit 0
    ;;
  *)
    echo "unknown FAKE_PG_DUMP_MODE '${FAKE_PG_DUMP_MODE}'" >&2
    exit 64
    ;;
esac
