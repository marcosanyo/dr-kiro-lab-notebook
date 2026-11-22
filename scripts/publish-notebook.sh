#!/bin/sh
# Publish the lab notebook on AWS: a private S3 bucket behind CloudFront (deploy/notebook-site.yaml).
#   sh scripts/publish-notebook.sh create  --profile P --region R --stack S --bucket B
#   sh scripts/publish-notebook.sh publish --profile P --region R --stack S --bucket B
# create:  deploys the stack S (creates it, or updates it when it exists). Bucket B is the new bucket's name.
# publish: builds the site into a new empty folder under the system temporary folder, the same notebook-build
#          steps as scripts/view-notebook.sh, syncs it to bucket B (files that are no longer built are deleted),
#          clears the CloudFront cache, and prints the public address. The stack must exist; run create first.
# All four options are required; none has a default. The script stores no keys: the AWS CLI reads the named
# profile. A failing command stops the script with its own message. Needs `uv` and the AWS CLI.
# POSIX sh.
set -e
cd "$(dirname "$0")/.." || exit 2

usage() {
    echo "publish-notebook: usage: sh scripts/publish-notebook.sh create|publish --profile P --region R --stack S --bucket B" >&2
    exit 2
}

[ $# -ge 1 ] || usage
action=$1
shift
case "$action" in
    create | publish) ;;
    *) echo "publish-notebook: unknown action '$action' (use create or publish)" >&2; exit 2 ;;
esac

profile=""
region=""
stack=""
bucket=""
while [ $# -gt 0 ]; do
    case "$1" in
        --profile | --region | --stack | --bucket)
            [ $# -ge 2 ] || { echo "publish-notebook: $1 needs a value" >&2; exit 2; }
            case "$1" in
                --profile) profile=$2 ;;
                --region) region=$2 ;;
                --stack) stack=$2 ;;
                --bucket) bucket=$2 ;;
            esac
            shift 2
            ;;
        *)
            echo "publish-notebook: unknown argument '$1' (use --profile, --region, --stack, --bucket)" >&2
            exit 2
            ;;
    esac
done
[ -n "$profile" ] || { echo "publish-notebook: --profile is required" >&2; exit 2; }
[ -n "$region" ] || { echo "publish-notebook: --region is required" >&2; exit 2; }
[ -n "$stack" ] || { echo "publish-notebook: --stack is required" >&2; exit 2; }
[ -n "$bucket" ] || { echo "publish-notebook: --bucket is required" >&2; exit 2; }

if [ "$action" = create ]; then
    aws cloudformation deploy \
        --profile "$profile" --region "$region" \
        --stack-name "$stack" \
        --template-file deploy/notebook-site.yaml \
        --parameter-overrides "BucketName=$bucket"
    echo "publish-notebook: stack $stack is up to date"
    exit 0
fi

# publish
stack_output() {
    aws cloudformation describe-stacks \
        --profile "$profile" --region "$region" \
        --stack-name "$stack" \
        --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" --output text
}
stack_bucket=$(stack_output BucketName)
distribution_id=$(stack_output DistributionId)
domain=$(stack_output DistributionDomainName)
for value in "$stack_bucket" "$distribution_id" "$domain"; do
    case "$value" in
        '' | None) echo "publish-notebook: stack $stack has no outputs; run create first" >&2; exit 1 ;;
    esac
done
if [ "$stack_bucket" != "$bucket" ]; then
    echo "publish-notebook: stack $stack uses bucket '$stack_bucket', not '$bucket'; nothing was published" >&2
    exit 1
fi

out=$(mktemp -d "${TMPDIR:-/tmp}/lab-notebook.XXXXXX") || exit 2
uv run --project notebook notebook-build \
    --sessions sessions \
    --requests build-from-spec/requests \
    --app wind-tunnel/notebook \
    --app body-lab/notebook \
    --layouts notebook/layouts.toml \
    --words notebook/commentary-words.txt \
    --scan-config body-lab/adapter/scan_sources.toml \
    --scan-config wind-tunnel/adapter/scan_sources.toml \
    --stop-list .kiro/blind-scan/stop-list.txt \
    --out "$out"
echo "publish-notebook: built into $out"

aws s3 sync "$out" "s3://$bucket" --delete \
    --profile "$profile" --region "$region"

aws cloudfront create-invalidation \
    --profile "$profile" --region "$region" \
    --distribution-id "$distribution_id" --paths "/*" > /dev/null
echo "publish-notebook: CloudFront cache clear requested for distribution $distribution_id"
echo "publish-notebook: published at https://$domain/"
