# Logging And Audit Support

## Overview

The application now has two separate logging mechanisms with different responsibilities:

- business audit trail
- technical application logging

This separation keeps operational accountability distinct from technical diagnostics.

## Audit Trail

Implementation:

- [audit_trail_service.py](/C:/Users/bornv/OneDrive/Documenten/Transportdocuments/src/logistics_app/application/services/audit_trail_service.py)
- [audit_log.py](/C:/Users/bornv/OneDrive/Documenten/Transportdocuments/src/logistics_app/data/models/audit_log.py)

The audit service is explicit by design:

- it does not use ORM event hooks
- it does not write records automatically behind unrelated saves
- application code must call the relevant audit method when a business action is confirmed

Supported business actions include:

- delivery slip created
- delivery slip changed
- document uploaded
- signed CMR uploaded
- document readiness confirmed by transport
- pallet assigned
- pallet moved
- pallet marked as loaded
- print instruction changed
- print action requested
- status changed

Audit records include:

- timestamp
- entity type
- entity id
- action type
- acting user
- source system
- related delivery, pallet, document, or split transport ids
- structured event details

## Application Logging

Implementation:

- [application_logging_service.py](/C:/Users/bornv/OneDrive/Documenten/Transportdocuments/src/logistics_app/application/services/application_logging_service.py)
- [setup.py](/C:/Users/bornv/OneDrive/Documenten/Transportdocuments/src/logistics_app/infrastructure/logging/setup.py)
- [logger_factory.py](/C:/Users/bornv/OneDrive/Documenten/Transportdocuments/src/logistics_app/infrastructure/logging/logger_factory.py)
- [application_log.py](/C:/Users/bornv/OneDrive/Documenten/Transportdocuments/src/logistics_app/data/models/application_log.py)

Application logging supports:

- exceptions
- database errors
- storage failures
- print failures
- validation errors

Behavior:

- logs are emitted through the standard Python logging framework
- output remains structured JSON
- important events can also be persisted to the `application_logs` table
- persistence is controlled by configuration

## Operational Guidance

Use the audit service when:

- a business action has legal, operational, or accountability importance

Use the application logging service when:

- the event is mainly technical
- support staff need diagnostic detail
- the event represents a failure, warning, or exception path

## No Hidden Side Effects

This implementation intentionally avoids:

- SQLAlchemy listeners that silently create logs
- automatic audit writes on every update
- implicit persistence inside model constructors

That makes the write path easier for an internal IT team to follow and maintain.
