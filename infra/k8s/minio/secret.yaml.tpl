apiVersion: v1
kind: Secret
metadata:
  name: minio-secret
  namespace: mkc-dev
  labels:
    app.kubernetes.io/part-of: mkc
type: Opaque
stringData:
  root-user: "mkc"
  root-password: "${MINIO_ROOT_PASSWORD}"
# NOTE: This file is generated from secret.yaml.tpl by render-secrets.sh.
# Do NOT commit the rendered secret.yaml to Git.
