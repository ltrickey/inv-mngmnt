# Lambda function and EventBridge Scheduler infrastructure for report generation

# Zip the report_lambda/ directory at plan time
data "archive_file" "report_lambda" {
  type        = "zip"
  source_dir  = "${path.module}/../report_lambda"
  output_path = "${path.module}/../deploy/report_lambda.zip"
}

resource "aws_lambda_function" "report_generator" {
  filename         = data.archive_file.report_lambda.output_path
  source_code_hash = data.archive_file.report_lambda.output_base64sha256
  function_name    = "${local.name_prefix}-report-generator"
  role             = data.aws_iam_role.ec2_role.arn
  handler          = "handler.lambda_handler"
  runtime          = "python3.12"
  timeout          = 300 # 5 minutes — large reports may scan many DynamoDB pages
  memory_size      = 256

  environment {
    variables = {
      SALES_EVENTS_TABLE     = aws_dynamodb_table.sales_events.name
      PRODUCTS_TABLE         = aws_dynamodb_table.products.name
      REPORTS_BUCKET         = aws_s3_bucket.reports.id
      REPORT_SCHEDULES_TABLE = aws_dynamodb_table.report_schedules.name
      REPORT_RESULTS_TABLE   = aws_dynamodb_table.report_results.name
    }
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-report-generator"
  })
}

# Allow EventBridge Scheduler to invoke the Lambda
resource "aws_lambda_permission" "allow_eventbridge_scheduler" {
  statement_id  = "AllowEventBridgeScheduler"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.report_generator.function_name
  principal     = "scheduler.amazonaws.com"
}

# Schedule group — all dynamically-created per-schedule rules go here
# The BFF creates individual schedules inside this group via boto3
resource "aws_scheduler_schedule_group" "reports" {
  name = "${local.name_prefix}-reports"

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-report-schedules"
  })
}
