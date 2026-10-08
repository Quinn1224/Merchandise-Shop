#!/bin/sh
set -e

# Rechte für die gemappten Host-Volumes automatisch korrigieren
chown -R appuser:appuser /code/data /code/media

# Befehl als appuser ausführen (droppt root-Rechte)
exec gosu appuser "$@"