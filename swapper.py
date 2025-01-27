"""
This project is developed by Haofan Wang to support face swap in single frame. Multi-frame will be supported soon!

It is highly built on the top of insightface, sd-webui-roop and CodeFormer.
"""

import copy
import os
from typing import List, Union

import cv2
import insightface
import numpy as np
from PIL import Image

from restoration import *


def getFaceSwapModel(model_path: str):
    model = insightface.model_zoo.get_model(model_path)
    return model


def getFaceAnalyser(model_path: str, det_size=(320, 320)):
    face_analyser = insightface.app.FaceAnalysis(name="buffalo_l", root="./checkpoints")
    face_analyser.prepare(ctx_id=0, det_size=det_size)
    return face_analyser


def get_one_face(face_analyser, frame: np.ndarray):
    face = face_analyser.get(frame)
    try:
        return min(face, key=lambda x: x.bbox[0])
    except ValueError:
        return None


def get_many_faces(face_analyser, frame: np.ndarray):
    """
    get faces from left to right by order
    """
    try:
        face = face_analyser.get(frame)
        return sorted(face, key=lambda x: x.bbox[0])
    except IndexError:
        return None


def swap_face(
    face_swapper, source_faces, target_faces, source_index, target_index, temp_frame
):
    """
    paste source_face on target image
    """
    print("=" * 40)
    print(len(source_faces))
    print(source_index)
    source_face = source_faces[source_index]
    target_face = target_faces[target_index]

    return face_swapper.get(temp_frame, target_face, source_face, paste_back=True)


def process(
    source_img: Union[Image.Image, List],
    target_img: Image.Image,
    source_indexes: str,
    target_indexes: str,
    model: str,
):
    # load face_analyser
    face_analyser = getFaceAnalyser(model)

    # load face_swapper
    model_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), model)
    face_swapper = getFaceSwapModel(model_path)

    # read target image
    target_img = cv2.cvtColor(np.array(target_img), cv2.COLOR_RGB2BGR)

    # detect faces that will be replaced in the target image
    target_faces = get_many_faces(face_analyser, target_img)
    num_target_faces = len(target_faces)
    num_source_images = len(source_img)

    print(f"Found num faces on the target image: {len(target_faces)}")

    print(num_source_images, num_target_faces)

    for item in target_faces:
        print(item["bbox"])

    if target_faces is not None:
        temp_frame = copy.deepcopy(target_img)
        if isinstance(source_img, list) and num_source_images == num_target_faces:
            print("Replacing faces in target image from the left to the right by order")

            # For each target face,
            for i in range(num_target_faces):
                source_faces = get_many_faces(
                    face_analyser,
                    cv2.cvtColor(np.array(source_img[i]), cv2.COLOR_RGB2BGR),
                )
                print(f"Found this many source faces: {len(source_faces)}")
                source_index = i if i < len(source_faces) - 1 else len(source_faces) - 1
                target_index = i

                if source_faces is None:
                    raise Exception("No source faces found!")

                temp_frame = swap_face(
                    face_swapper,
                    source_faces,
                    target_faces,
                    source_index,
                    target_index,
                    temp_frame,
                )
        elif num_source_images == 1:
            # detect source faces that will be replaced into the target image
            source_faces = get_many_faces(
                face_analyser, cv2.cvtColor(np.array(source_img[0]), cv2.COLOR_RGB2BGR)
            )

            num_source_faces = len(source_faces)
            print(f"Source faces: {num_source_faces}")
            print(f"Target faces: {num_target_faces}")

            if source_faces is None:
                raise Exception("No source faces found!")

            if target_indexes == "-1":
                if num_source_faces == 1:
                    print(
                        "Replacing all faces in target image with the same face from the source image"
                    )
                    num_iterations = num_target_faces
                elif num_source_faces < num_target_faces:
                    print(
                        "There are less faces in the source image than the target image, replacing as many as we can"
                    )
                    num_iterations = num_source_faces
                elif num_target_faces < num_source_faces:
                    print(
                        "There are less faces in the target image than the source image, replacing as many as we can"
                    )
                    num_iterations = num_target_faces
                else:
                    print(
                        "Replacing all faces in the target image with the faces from the source image"
                    )
                    num_iterations = num_target_faces

                for i in range(num_iterations):
                    source_index = 0 if num_source_faces == 1 else i
                    target_index = i

                    temp_frame = swap_face(
                        face_swapper,
                        source_faces,
                        target_faces,
                        source_index,
                        target_index,
                        temp_frame,
                    )
            else:
                print(
                    "Replacing specific face(s) in the target image with specific face(s) from the source image"
                )

                if source_indexes == "-1":
                    source_indexes = ",".join(
                        map(lambda x: str(x), range(num_source_faces))
                    )

                if target_indexes == "-1":
                    target_indexes = ",".join(
                        map(lambda x: str(x), range(num_target_faces))
                    )

                source_indexes = source_indexes.split(",")
                target_indexes = target_indexes.split(",")
                num_source_faces_to_swap = len(source_indexes)
                num_target_faces_to_swap = len(target_indexes)

                if num_source_faces_to_swap > num_source_faces:
                    raise Exception(
                        "Number of source indexes is greater than the number of faces in the source image"
                    )

                if num_target_faces_to_swap > num_target_faces:
                    raise Exception(
                        "Number of target indexes is greater than the number of faces in the target image"
                    )

                if num_source_faces_to_swap > num_target_faces_to_swap:
                    num_iterations = num_source_faces_to_swap
                else:
                    num_iterations = num_target_faces_to_swap

                if num_source_faces_to_swap == num_target_faces_to_swap:
                    for index in range(num_iterations):
                        source_index = int(source_indexes[index])
                        target_index = int(target_indexes[index])

                        if source_index > num_source_faces - 1:
                            raise ValueError(
                                f"Source index {source_index} is higher than the number of faces in the source image"
                            )

                        if target_index > num_target_faces - 1:
                            raise ValueError(
                                f"Target index {target_index} is higher than the number of faces in the target image"
                            )

                        temp_frame = swap_face(
                            face_swapper,
                            source_faces,
                            target_faces,
                            source_index,
                            target_index,
                            temp_frame,
                        )
        else:
            raise Exception("Unsupported face configuration")
        result = temp_frame
    else:
        print("No target faces found!")

    result_image = Image.fromarray(cv2.cvtColor(result, cv2.COLOR_BGR2RGB))
    return result_image


def do_swap(
    source_img_pths=["./data/man1.jpeg", "./data/man2.jpeg"],
    target_img="./data/mans1.jpeg",
    source_indexes="-1",
    target_indexes="-1",
    face_restore=True,
    background_enhance=True,
    face_upsample=True,
    upscale=2,
    codeformer_fidelity=0.5,
    output_img="result.png",
):
    """
    ARGS:
        source_indexes: Comma separated list of the face indexes to use (left to right) in the source image, starting at 0 (-1 uses all faces in the source image)
        target_indexes: Comma separated list of the face indexes to swap (left to right) in the target image, starting at 0 (-1
         swaps all faces in the target image)
        face_restore (BOOL): The flag for face restoration
        background_enhance (BOOL): The flag for background enhancement.
        face_unsample (BOOL): The flag for face upsample.
        upscale (INT): The upscale value, up to 4.
        codeformer_fidelity (FLOAT): The codeformer fidelity.
    """

    target_img_path = target_img

    source_img = [Image.open(img_path) for img_path in source_img_pths]
    target_img = Image.open(target_img_path)

    # download from https://huggingface.co/deepinsight/inswapper/tree/main
    model = "./checkpoints/inswapper_128.onnx"

    print(f"There is {len(source_img)} source images")
    print(f"There is 1 target images")
    print(f"Processing source indexes {source_indexes}")
    print(f"Process target indexes {target_indexes}")

    result_image = process(
        source_img, target_img, source_indexes, target_indexes, model
    )

    if face_restore:
        # make sure the ckpts downloaded successfully
        check_ckpts()

        # https://huggingface.co/spaces/sczhou/CodeFormer
        upsampler = set_realesrgan()
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        codeformer_net = ARCH_REGISTRY.get("CodeFormer")(
            dim_embd=512,
            codebook_size=1024,
            n_head=8,
            n_layers=9,
            connect_list=["32", "64", "128", "256"],
        ).to(device)
        ckpt_path = "CodeFormer/CodeFormer/weights/CodeFormer/codeformer.pth"
        checkpoint = torch.load(ckpt_path)["params_ema"]
        codeformer_net.load_state_dict(checkpoint)
        codeformer_net.eval()

        result_image = cv2.cvtColor(np.array(result_image), cv2.COLOR_RGB2BGR)
        result_image = face_restoration(
            result_image,
            background_enhance,
            face_upsample,
            upscale,
            codeformer_fidelity,
            upsampler,
            codeformer_net,
            device,
        )
        result_image = Image.fromarray(result_image)

    # save result
    result_image.save(output_img)
    print(f"Result saved successfully: {output_img}")

    return


if __name__ == "__main__":
    do_swap()
