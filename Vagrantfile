# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure(2) do |config|
  config.vm.box = "hashicorp/precise32"
  config.vm.network :forwarded_port, guest: 5672, host: 5672
  config.vm.network :forwarded_port, guest: 15672, host: 15672
  config.vm.network :forwarded_port, guest: 55672, host: 55672
  config.vm.network :forwarded_port, guest: 6379, host: 6379

  config.vm.provision "ansible" do |ansible|
    ansible.playbook = "playbook.yml"
  end
end
