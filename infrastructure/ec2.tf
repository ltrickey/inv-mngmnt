resource "aws_instance" "inventory_api" {
    ami = data.aws_ami.amazon_linux.id
    instance_type = "t4g.micro"
    iam_instance_profile   = local.instance_profile_name
    vpc_security_group_ids = [aws_security_group.inventory_api.id]
    subnet_id              = data.aws_subnet.default.id
    key_name               = var.ec2_key_pair

    tags = merge(local.common_tags, {
      Name = "${local.name_prefix}-inventory-api"
    })

  lifecycle {
    create_before_destroy = true
  }

}