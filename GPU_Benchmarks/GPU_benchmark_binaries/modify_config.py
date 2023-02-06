import argparse
import os 

def modify_config(config_file, gpu_id):
    """Modifies the GPU DEVICE number in the config file."""
    with open(config_file, "r") as template:
        template_lines = template.readlines()
    for i in range(len(template_lines)):
        if "GPU_DEVICE" in template_lines[i]:
            template_lines[i]='GPU_DEVICE={}\n'.format(
                gpu_id)
    execution_script="".join(template_lines)
    with open(config_file, "w") as script:
        script.write(execution_script)
    os.popen("chmod 777 '{}'".format(config_file))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--nas_config_repo', 
                        help='Path to the config file.', 
                        type=str, default='/root/NPB-GPU/CUDA/config/gpu.config')
    parser.add_argument('--gpu_id', 
                        help='GPU id', 
                        type=str, default='0')
    args = parser.parse_args()
    modify_config(args.nas_config_repo, args.gpu_id)
    
if __name__ == '__main__':
    main()