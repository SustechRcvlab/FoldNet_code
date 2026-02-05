import os
import argparse
from pathlib import Path

from garmentds.gentexture.paint import Painter

def main(args):
    painter = Painter(client=args.client, pipeline=args.pipeline, 
                    use_same_front_back=args.use_same_front_back,
                    use_symmetric_texture=args.use_symmetric_texture)

    if args.output_dir is None:
        args.output_dir = Path(os.environ["FOLDNET_BASE_DIR"]) / "data" / "texture"

    for i in range(args.start_idx, args.start_idx + args.num_to_generate):
        output_dir = os.path.join(args.output_dir, str(i))
        os.makedirs(output_dir, exist_ok=True)
        painter.generate_texture_images(category=args.category, output_dir=output_dir, texture_ready_to_use=None)

if __name__ == "__main__":
    """
        Use the following script to generate ready-to-use texture images.
    """
    os.environ["FOLDNET_BASE_DIR"] = (Path(__file__) / ".." / ".." / "..").resolve().__str__()

    parser = argparse.ArgumentParser()
    parser.add_argument("--category", type=str, default="tshirt_sp")
    parser.add_argument("--pipeline", type=str, default="stabilityai/stable-diffusion-3.5-large")
    parser.add_argument("--client", type=str, default=None)
    parser.add_argument("--use_same_front_back", action="store_true")
    parser.add_argument("--use_symmetric_texture", action="store_true")
    parser.add_argument("--start_idx", type=int, default=0)
    parser.add_argument("--num_to_generate", type=int, default=1)
    parser.add_argument("--output_dir", type=str, default=None)

    args = parser.parse_args()

    main(args)