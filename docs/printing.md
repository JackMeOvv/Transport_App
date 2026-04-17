# Printing Logic

## Overview

Printing is split into two clear responsibilities:

- transport defines required document copies
- warehouse requests and executes actual print jobs

Implementation:

- [print_instruction_service.py](../src/logistics_app/application/services/print_instruction_service.py)
- [print_job_service.py](../src/logistics_app/application/services/print_job_service.py)

## Print Instructions

Print instructions represent transport-defined copy requirements for a document type.

They track:

- delivery or split transport scope
- document type
- required copy count
- optional printer role
- whether the instruction is mandatory

The service can calculate:

- required copies
- printed copies
- remaining copies

## Print Jobs

Print jobs represent actual warehouse print requests.

They track:

- delivery
- optional document
- optional split transport
- document type
- target type
- printer role
- printer name
- whether a manual printer override was used
- requested copies
- printed copies
- reprint source job when applicable
- status and timestamps

## Printer Routing

Default printer routing is controlled by configuration.

Two layers are involved:

1. document type to printer role mapping
2. printer role to actual printer name mapping

This lets IT change physical printers without changing print logic code.

Examples are configured through:

- `LOGISTICS_APP_PRINTERS__DOCUMENT_TYPE_MAPPING__PACKING_SLIP`
- `LOGISTICS_APP_PRINTERS__DOCUMENT_TYPE_MAPPING__CMR`
- `LOGISTICS_APP_PRINTERS__DOCUMENT_TYPE_MAPPING__SIGNED_CMR`
- `LOGISTICS_APP_PRINTERS__DOCUMENT_TYPE_MAPPING__CERTIFICATE`
- `LOGISTICS_APP_PRINTERS__DOCUMENT_TYPE_MAPPING__STICKER`
- `LOGISTICS_APP_PRINTERS__DOCUMENT_TYPE_MAPPING__TRANSPORT_DOCUMENT`
- `LOGISTICS_APP_PRINTERS__DOCUMENT_TYPE_MAPPING__OTHER`

The mapped values refer to fields inside printer defaults, such as:

- `warehouse_main_printer`
- `loading_dock_printer`
- `office_printer`
- `label_printer`

## Reprints

Reprints are modeled as separate print jobs.

That means:

- the original print request remains visible
- the reprint has its own queue and result state
- the relationship to the original job is preserved
- every print action is auditable

## Logging

Every print request is written to the business audit trail.

Print failures are also written to the technical application log with structured context.
