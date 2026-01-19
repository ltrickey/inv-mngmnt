# Todo: take in instance type as var?
resource "aws_instance" "product_catalogue" {
    ami = data.aws_ami.amazon_linux.id
    instance_type = "t4g.micro" 
    iam_instance_profile   = data.aws_iam_instance_profile.LabInstanceProfile.name
    vpc_security_group_ids = [aws_security_group.product_catalogue.id]
    subnet_id              = data.aws_subnet.default.id
    key_name               = var.ec2_key_pair

    tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-tasks-service"
  })

  lifecycle {
    create_before_destroy = true
  }

}