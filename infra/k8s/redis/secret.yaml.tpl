apiVersion: v1
kind: Secret
metadata:
  name: redis-secret
  namespace: mkc-dev
  labels:
    app.kubernetes.io/part-of: mkc
type: Opaque
stringData:
  password: "${REDIS_PASSWORD}"
# NOTE: This file is generated from secret.yaml.tpl by render-secrets.sh.
# Do NOT commit the rendered secret.yaml to Git.
