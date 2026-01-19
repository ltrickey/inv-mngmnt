# Todo: take in instance type as var?
resource "aws_instance" "server" {
    ami = data.aws_ami.amazon_linux.id
    instance_type = "t4g.micro" 

    iam_instance_profile   = data.aws_iam_instance_profile.LabInstanceProfile.name
    vpc_security_group_ids = [aws_security_group.tasks_service.id]
    subnet_id              = data.aws_subnet.default.id
    key_name               = var.ec2_key_pair
}