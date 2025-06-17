# xlabel_cli.py — MIT License
# Author: Eraldo Marques
# Created: 2025-06-16 (Project Inception)
# This file is part of the XLabel project.
# See LICENSE.txt for full license terms. This header should be retained.

import argparse
import json
import sys
import os
import logging
from PIL import Image 
import glob
import xml.etree.ElementTree as ET
import datetime 

import xcreator
import xreader
import xlabel_format_converters as xlabel_converters 

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
cli_logger = logging.getLogger("xlabel_cli") 

SUPPORTED_IMAGE_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.webp']
SUPPORTED_XLABEL_PNG_EXTENSIONS = ['.png'] 

# --- Batch Create ---
def handle_create_batch(args):
    if not os.path.isdir(args.input_image_dir):
        cli_logger.error(f"Error: Input image directory '{args.input_image_dir}' not found or not a directory.")
        sys.exit(1)
    if not os.path.isdir(args.input_json_dir):
        cli_logger.error(f"Error: Input JSON directory '{args.input_json_dir}' not found or not a directory.")
        sys.exit(1)
    
    output_dir = args.output_xlabel_dir
    if not os.path.isdir(output_dir):
        cli_logger.info(f"Output directory '{output_dir}' not found. Creating it.")
        try:
            os.makedirs(output_dir, exist_ok=True)
        except OSError as e:
            cli_logger.error(f"Error: Could not create output directory '{output_dir}': {e}")
            sys.exit(1)

    processed_count = 0
    error_count = 0
    image_files_found = []
    for ext in SUPPORTED_IMAGE_EXTENSIONS:
        image_files_found.extend(glob.glob(os.path.join(args.input_image_dir, f"*{ext}")))
        image_files_found.extend(glob.glob(os.path.join(args.input_image_dir, f"*{ext.upper()}"))) 

    if not image_files_found:
        cli_logger.warning(f"No supported image files found in '{args.input_image_dir}'. Supported: {SUPPORTED_IMAGE_EXTENSIONS}")
        return

    cli_logger.info(f"Found {len(image_files_found)} images to process in '{args.input_image_dir}'.")

    for img_path in image_files_found:
        base_filename_no_ext = os.path.splitext(os.path.basename(img_path))[0]
        json_metadata_path = os.path.join(args.input_json_dir, base_filename_no_ext + ".json")
        output_xlabel_png_path = os.path.join(output_dir, base_filename_no_ext + ".png") 

        cli_logger.info(f"Processing image: {img_path}")
        if not os.path.exists(json_metadata_path):
            cli_logger.error(f"  Error: Metadata file '{json_metadata_path}' not found for image '{img_path}'. Skipping.")
            error_count += 1
            continue
        
        try:
            with open(json_metadata_path, 'r') as f:
                metadata_from_json = json.load(f)
            
            xcreator.add_xlabel_metadata_to_png(img_path, output_xlabel_png_path, metadata_from_json, args.overwrite)
            cli_logger.info(f"  Successfully created XLabel PNG: {output_xlabel_png_path}")
            processed_count += 1
        except FileNotFoundError as e: 
            cli_logger.error(f"  Error processing '{img_path}': File not found - {e}")
            error_count += 1
        except json.JSONDecodeError as e:
            cli_logger.error(f"  Error: Invalid JSON in '{json_metadata_path}': {e}")
            error_count += 1
        except (xcreator.XLabelFormatError, xcreator.XLabelError) as e: 
            cli_logger.error(f"  XLabel Creation/Format Error for '{img_path}': {e}")
            error_count += 1
        except FileExistsError as e: 
            cli_logger.error(f"  Output Error for '{output_xlabel_png_path}': {e}")
            error_count += 1
        except Exception as e: 
            cli_logger.error(f"  An unexpected error occurred for '{img_path}': {e}", exc_info=args.debug)
            error_count += 1
            
    cli_logger.info(f"\nBatch 'create' summary:")
    cli_logger.info(f"  Successfully processed: {processed_count} images.")
    cli_logger.info(f"  Errors encountered: {error_count} images.")
    if error_count > 0:
        sys.exit(1)

# --- Single Create ---
def handle_create_single(args):
    try:
        with open(args.json_metadata_single, 'r') as f:
            metadata = json.load(f)
        xcreator.add_xlabel_metadata_to_png(args.input_image_single, args.output_xlabel_png_single, metadata, args.overwrite)
        cli_logger.info(f"Successfully created XLabel PNG: {args.output_xlabel_png_single}")
    except FileNotFoundError as e:
        cli_logger.error(f"Error: File not found - {e}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        cli_logger.error(f"Error: Invalid JSON metadata file '{args.json_metadata_single}': {e}")
        sys.exit(1)
    except (xcreator.XLabelFormatError, xcreator.XLabelError) as e:
        cli_logger.error(f"XLabel Creation/Format Error: {e}")
        sys.exit(1)
    except FileExistsError as e:
        cli_logger.error(f"Output Error: {e}")
        sys.exit(1)
    except Exception as e:
        cli_logger.error(f"An unexpected error occurred during 'create single': {e}", exc_info=args.debug)
        sys.exit(1)

# --- Single Read ---
def handle_read_single(args):
    try:
        metadata = xreader.read_xlabel_metadata_from_png(args.input_xlabel_png_single)
        if metadata:
            if args.output_json_single:
                output_dir = os.path.dirname(args.output_json_single)
                if output_dir and not os.path.exists(output_dir):
                    os.makedirs(output_dir, exist_ok=True)
                with open(args.output_json_single, 'w') as f:
                    json.dump(metadata, f, indent=args.indent)
                cli_logger.info(f"Metadata extracted to: {args.output_json_single}")
            else:
                print(json.dumps(metadata, indent=args.indent))
        else:
            cli_logger.warning(f"No XLabel metadata (xlDa chunk) found in '{args.input_xlabel_png_single}'.")
    except FileNotFoundError as e:
        cli_logger.error(f"Error: Input XLabel PNG not found - {e}")
        sys.exit(1)
    except (xreader.XLabelFormatError, xreader.XLabelVersionError, xreader.XLabelError) as e: 
        cli_logger.error(f"XLabel Read Error from '{args.input_xlabel_png_single}': {e}")
        sys.exit(1)
    except Exception as e:
        cli_logger.error(f"An unexpected error occurred during 'read single': {e}", exc_info=args.debug)
        sys.exit(1)

# --- Batch Read (Exports to Sidecar JSONs) ---
def handle_read_batch(args):
    if not os.path.isdir(args.input_xlabel_dir):
        cli_logger.error(f"Error: Input XLabel PNG directory '{args.input_xlabel_dir}' not found or not a directory.")
        sys.exit(1)
    
    output_dir = args.output_json_dir # This is the directory for sidecar JSONs
    if not os.path.isdir(output_dir):
        cli_logger.info(f"Output JSON directory '{output_dir}' not found. Creating it.")
        try:
            os.makedirs(output_dir, exist_ok=True)
        except OSError as e:
            cli_logger.error(f"Error: Could not create output directory '{output_dir}': {e}")
            sys.exit(1)

    processed_count = 0
    error_count = 0
    xlabel_png_files_found = []
    for ext in SUPPORTED_XLABEL_PNG_EXTENSIONS: 
        xlabel_png_files_found.extend(glob.glob(os.path.join(args.input_xlabel_dir, f"*{ext}")))
        xlabel_png_files_found.extend(glob.glob(os.path.join(args.input_xlabel_dir, f"*{ext.upper()}")))

    if not xlabel_png_files_found:
        cli_logger.warning(f"No XLabel PNG files (ending in {SUPPORTED_XLABEL_PNG_EXTENSIONS}) found in '{args.input_xlabel_dir}'.")
        return

    cli_logger.info(f"Found {len(xlabel_png_files_found)} XLabel PNGs to process in '{args.input_xlabel_dir}'. Exporting metadata to JSON sidecar files.")

    for png_path in xlabel_png_files_found:
        base_filename_no_ext = os.path.splitext(os.path.basename(png_path))[0]
        output_json_path = os.path.join(output_dir, base_filename_no_ext + ".json")
        cli_logger.info(f"Processing XLabel PNG: {png_path}")
        try:
            metadata = xreader.read_xlabel_metadata_from_png(png_path)
            if metadata: 
                with open(output_json_path, 'w') as f:
                    json.dump(metadata, f, indent=args.indent)
                cli_logger.info(f"  Successfully extracted metadata to sidecar JSON: {output_json_path}")
                processed_count += 1
            else: 
                cli_logger.warning(f"  No XLabel metadata (xlDa chunk) found in '{png_path}'. Skipping JSON output for this file.")
        except (xreader.XLabelError) as e: 
            cli_logger.error(f"  Error reading XLabel data from '{png_path}': {e}", exc_info=args.debug)
            error_count += 1
        except Exception as e: 
            cli_logger.error(f"  An unexpected error occurred while processing '{png_path}': {e}", exc_info=args.debug)
            error_count += 1
            
    cli_logger.info(f"\nBatch 'read' (export to sidecar JSONs) summary:")
    cli_logger.info(f"  Successfully processed (metadata extracted): {processed_count} files.")
    cli_logger.info(f"  Errors encountered during XLabel processing: {error_count} files.")
    if error_count > 0:
        sys.exit(1)

# --- Convert Single (2xlabel) ---
def handle_convert_2xlabel_single(args):
    cli_logger.debug(f"Args for convert_2xlabel_single: {args}")
    try:
        if not args.input_image: cli_logger.error("Error: --input-image is required for single '2xlabel' mode."); sys.exit(1)
        if not args.output_xlabel_png: cli_logger.error("Error: --output-xlabel-png is required for single '2xlabel' mode."); sys.exit(1)
        
        metadata, img_width, img_height = None, None, None
        try:
            with Image.open(args.input_image) as img:
                img_width, img_height = img.width, img.height
        except FileNotFoundError:
            cli_logger.error(f"Error: Input image '{args.input_image}' not found."); sys.exit(1)
        except Exception as e: 
            cli_logger.error(f"Error opening input image '{args.input_image}': {e}"); sys.exit(1)

        image_filename_in_source_fmt = os.path.basename(args.input_image) 

        if args.from_format == "coco":
            if not args.input_coco: cli_logger.error("Error: --input-coco is required for coco to XLabel conversion."); sys.exit(1)
            metadata = xlabel_converters.coco_to_xlabel_metadata(args.input_coco, image_filename_in_source_fmt)
        elif args.from_format == "voc":
            if not args.input_voc: cli_logger.error("Error: --input-voc is required for voc to XLabel conversion."); sys.exit(1)
            metadata = xlabel_converters.voc_to_xlabel_metadata(args.input_voc)
        elif args.from_format == "yolo":
            if not args.input_yolo_txt: cli_logger.error("Error: --input-yolo-txt is required for yolo to XLabel conversion."); sys.exit(1)
            if not args.yolo_class_names: cli_logger.error("Error: --yolo-class-names is required for yolo to XLabel conversion."); sys.exit(1)
            metadata = xlabel_converters.yolo_to_xlabel_metadata(args.input_yolo_txt, args.yolo_class_names, img_width, img_height, image_filename_in_source_fmt)
        
        if metadata:
            metadata["image_properties"]["filename"] = os.path.basename(args.input_image) 
            metadata["image_properties"]["width"] = img_width
            metadata["image_properties"]["height"] = img_height
            xcreator.add_xlabel_metadata_to_png(args.input_image, args.output_xlabel_png, metadata, args.overwrite)
            cli_logger.info(f"Successfully converted {args.from_format} for '{args.input_image}' to XLabel PNG: {args.output_xlabel_png}")
        else:
            cli_logger.error(f"Conversion from {args.from_format} for '{args.input_image}' failed: No metadata was generated by the converter."); sys.exit(1)
            
    except xlabel_converters.XLabelConversionError as e:
        cli_logger.error(f"Conversion Error (2xlabel single): {e}", exc_info=args.debug); sys.exit(1)
    except (xcreator.XLabelError, xreader.XLabelError) as e: 
        cli_logger.error(f"XLabel System Error (2xlabel single): {e}", exc_info=args.debug); sys.exit(1)
    except Exception as e:
        cli_logger.error(f"An unexpected error occurred (convert 2xlabel single): {e}", exc_info=args.debug); sys.exit(1)

# --- Convert Batch (2xlabel) ---
def handle_convert_2xlabel_batch(args):
    cli_logger.debug(f"Args for convert_2xlabel_batch: {args}")
    if not args.input_image_dir or not os.path.isdir(args.input_image_dir):
        cli_logger.error(f"Error: Input image directory (--input-image-dir) '{args.input_image_dir}' not found or not specified for batch mode."); sys.exit(1)
    if not args.output_xlabel_dir :
        cli_logger.error(f"Error: Output XLabel directory (--output-xlabel-dir) must be specified for batch '2xlabel' mode."); sys.exit(1)
    elif not os.path.isdir(args.output_xlabel_dir):
        cli_logger.info(f"Output XLabel directory '{args.output_xlabel_dir}' not found. Creating it.")
        try: os.makedirs(args.output_xlabel_dir, exist_ok=True)
        except OSError as e: cli_logger.error(f"Error creating output directory '{args.output_xlabel_dir}': {e}"); sys.exit(1)


    processed_count = 0; error_count = 0
    image_files_found = []
    for ext in SUPPORTED_IMAGE_EXTENSIONS:
        image_files_found.extend(glob.glob(os.path.join(args.input_image_dir, f"*{ext}")))
        image_files_found.extend(glob.glob(os.path.join(args.input_image_dir, f"*{ext.upper()}")))
    
    if not image_files_found: cli_logger.warning(f"No images found in '{args.input_image_dir}'."); return
    cli_logger.info(f"Found {len(image_files_found)} images in '{args.input_image_dir}' for batch conversion to XLabel from {args.from_format}.")

    if args.from_format == "coco" and not (args.input_coco and os.path.isfile(args.input_coco)):
        cli_logger.error(f"COCO batch conversion: --input-coco file '{args.input_coco}' not found or not specified."); sys.exit(1)
    if args.from_format == "voc" and not (args.input_voc_dir and os.path.isdir(args.input_voc_dir)):
        cli_logger.error(f"VOC batch conversion: --input-voc-dir '{args.input_voc_dir}' not found or not specified."); sys.exit(1)
    if args.from_format == "yolo":
        if not (args.input_yolo_dir and os.path.isdir(args.input_yolo_dir)):
            cli_logger.error(f"YOLO batch conversion: --input-yolo-dir '{args.input_yolo_dir}' not found or not specified."); sys.exit(1)
        if not (args.yolo_class_names and os.path.isfile(args.yolo_class_names)):
            cli_logger.error(f"YOLO batch conversion: --yolo-class-names file '{args.yolo_class_names}' not found or not specified."); sys.exit(1)

    for img_path in image_files_found:
        img_basename = os.path.basename(img_path)
        img_name_no_ext = os.path.splitext(img_basename)[0]
        output_xlabel_png_path = os.path.join(args.output_xlabel_dir, img_name_no_ext + ".png") 
        cli_logger.info(f"Processing image: {img_path}")
        
        metadata = None
        try:
            with Image.open(img_path) as img_obj: img_width, img_height = img_obj.width, img_obj.height

            if args.from_format == "coco":
                metadata = xlabel_converters.coco_to_xlabel_metadata(args.input_coco, img_basename)
            elif args.from_format == "voc":
                voc_xml_path = os.path.join(args.input_voc_dir, img_name_no_ext + ".xml")
                if not os.path.isfile(voc_xml_path):
                    cli_logger.error(f"  VOC XML '{voc_xml_path}' not found for image '{img_basename}'. Skipping."); error_count+=1; continue
                metadata = xlabel_converters.voc_to_xlabel_metadata(voc_xml_path)
            elif args.from_format == "yolo":
                yolo_txt_path = os.path.join(args.input_yolo_dir, img_name_no_ext + ".txt")
                if not os.path.isfile(yolo_txt_path):
                    cli_logger.error(f"  YOLO TXT '{yolo_txt_path}' not found for image '{img_basename}'. Skipping."); error_count+=1; continue
                metadata = xlabel_converters.yolo_to_xlabel_metadata(yolo_txt_path, args.yolo_class_names, img_width, img_height, img_basename)

            if metadata:
                metadata["image_properties"]["filename"] = img_basename 
                metadata["image_properties"]["width"] = img_width
                metadata["image_properties"]["height"] = img_height
                xcreator.add_xlabel_metadata_to_png(img_path, output_xlabel_png_path, metadata, args.overwrite)
                cli_logger.info(f"  Successfully converted to XLabel PNG: {output_xlabel_png_path}"); processed_count += 1
            else: 
                cli_logger.error(f"  Conversion failed for '{img_path}': No metadata generated by converter."); error_count+=1
        
        except xlabel_converters.XLabelConversionError as e:
            cli_logger.error(f"  Conversion Error for '{img_path}': {e}", exc_info=args.debug); error_count+=1
        except (xcreator.XLabelError, xreader.XLabelError) as e:
             cli_logger.error(f"  XLabel System Error for '{img_path}': {e}", exc_info=args.debug); error_count+=1
        except Exception as e:
            cli_logger.error(f"  Unexpected error processing '{img_path}': {e}", exc_info=args.debug); error_count+=1
            
    cli_logger.info(f"\nBatch 'convert 2xlabel' summary: Processed: {processed_count}, Errors: {error_count}.")
    if error_count > 0: sys.exit(1)


# --- Convert Single (fromxlabel) ---
def handle_convert_fromxlabel_single(args):
    cli_logger.debug(f"Args for convert_fromxlabel_single: {args}")
    try:
        if not args.input_xlabel_png_conv: cli_logger.error("Error: --input-xlabel-png-conv required."); sys.exit(1)
        metadata = xreader.read_xlabel_metadata_from_png(args.input_xlabel_png_conv)
        if not metadata: 
            cli_logger.error(f"Failed to read XLabel metadata from '{args.input_xlabel_png_conv}'. File might not be an XLabel PNG or chunk is missing."); sys.exit(1)

        if args.to_format == "coco":
            if not args.output_coco: cli_logger.error("Error: --output-coco required."); sys.exit(1)
            image_entry, new_category_entries, annotation_entries, _, _, _ = \
                xlabel_converters.xlabel_metadata_to_coco_parts(
                    xlabel_data=metadata, current_image_id=1, category_map={}, 
                    current_max_category_id=0, current_annotation_id_start=1)
            coco_data = {
                "info": {"description": f"XLabel to COCO Export: {os.path.basename(args.input_xlabel_png_conv)}",
                         "version": xlabel_converters.REFINED_METADATA_VERSION, 
                         "year": datetime.datetime.strptime(xlabel_converters.coco_converter.CURRENT_DATE_TIME_UTC, "%Y-%m-%d %H:%M:%S").year,
                         "contributor": xlabel_converters.coco_converter.CURRENT_USER_LOGIN,
                         "date_created": xlabel_converters.coco_converter.CURRENT_DATE_TIME_UTC.replace(" ", "T") + "Z"},
                "licenses": [{"id": 1, "name": "Unknown", "url": ""}], 
                "images": [image_entry], "categories": new_category_entries, "annotations": annotation_entries
            }
            output_dir = os.path.dirname(args.output_coco)
            if output_dir and not os.path.exists(output_dir): os.makedirs(output_dir, exist_ok=True)
            with open(args.output_coco, 'w') as f: json.dump(coco_data, f, indent=args.indent)
            cli_logger.info(f"Converted XLabel PNG to COCO JSON: {args.output_coco}")

        elif args.to_format == "voc":
            if not args.output_voc: cli_logger.error("Error: --output-voc required."); sys.exit(1)
            voc_tree_root = xlabel_converters.xlabel_metadata_to_voc_xml_tree(metadata)
            output_dir = os.path.dirname(args.output_voc)
            if output_dir and not os.path.exists(output_dir): os.makedirs(output_dir, exist_ok=True)
            ET.ElementTree(voc_tree_root).write(args.output_voc, encoding="utf-8", xml_declaration=True)
            cli_logger.info(f"Converted XLabel PNG to VOC XML: {args.output_voc}")

        elif args.to_format == "yolo":
            if not args.output_yolo_txt: cli_logger.error("Error: --output-yolo-txt required."); sys.exit(1)
            if not args.yolo_class_names_output: cli_logger.error("Error: --yolo-class-names-output required."); sys.exit(1)
            yolo_lines = xlabel_converters.xlabel_metadata_to_yolo_lines(metadata)
            
            output_txt_dir = os.path.dirname(args.output_yolo_txt)
            if output_txt_dir and not os.path.exists(output_txt_dir): os.makedirs(output_txt_dir, exist_ok=True)
            with open(args.output_yolo_txt, 'w') as f:
                for line in yolo_lines: f.write(line + "\n")
            
            output_cls_dir = os.path.dirname(args.yolo_class_names_output)
            if output_cls_dir and not os.path.exists(output_cls_dir): os.makedirs(output_cls_dir, exist_ok=True)
            with open(args.yolo_class_names_output, 'w') as f:
                for name in metadata.get("class_names",[]): f.write(name + "\n")
            cli_logger.info(f"Converted XLabel PNG to YOLO: {args.output_yolo_txt} and {args.yolo_class_names_output}")

    except xlabel_converters.XLabelConversionError as e:
        cli_logger.error(f"Conversion Error (fromxlabel single): {e}", exc_info=args.debug); sys.exit(1)
    except (xreader.XLabelError, xcreator.XLabelError) as e: 
        cli_logger.error(f"XLabel System Error (fromxlabel single): {e}", exc_info=args.debug); sys.exit(1)
    except Exception as e:
        cli_logger.error(f"An unexpected error occurred (convert fromxlabel single): {e}", exc_info=args.debug); sys.exit(1)


# --- Convert Batch (fromxlabel) ---
def handle_convert_fromxlabel_batch(args):
    cli_logger.debug(f"Args for convert_fromxlabel_batch: {args}")
    if not args.input_xlabel_dir_conv or not os.path.isdir(args.input_xlabel_dir_conv):
        cli_logger.error(f"Error: Input XLabel directory (--input-xlabel-dir-conv) '{args.input_xlabel_dir_conv}' not found or not specified."); sys.exit(1)
    
    if args.to_format == "coco":
        if not args.output_coco: cli_logger.error("Error: --output-coco (single file path) is required for batch XLabel to COCO conversion."); sys.exit(1)
        coco_output_dir = os.path.dirname(args.output_coco)
        if coco_output_dir and not os.path.isdir(coco_output_dir):
            cli_logger.info(f"Output directory for COCO file '{coco_output_dir}' not found. Creating."); os.makedirs(coco_output_dir, exist_ok=True)
    elif args.to_format in ["voc", "yolo"]:
        if not args.output_dir_conv: 
            cli_logger.error(f"Error: --output-dir-conv is required for batch XLabel to {args.to_format}."); sys.exit(1)
        elif not os.path.isdir(args.output_dir_conv):
            cli_logger.info(f"Output directory (--output-dir-conv) '{args.output_dir_conv}' not found. Creating it.")
            try: os.makedirs(args.output_dir_conv, exist_ok=True)
            except OSError as e: cli_logger.error(f"Error creating output directory '{args.output_dir_conv}': {e}"); sys.exit(1)


    processed_count = 0; error_count = 0
    xlabel_png_files_found = []
    for ext in SUPPORTED_XLABEL_PNG_EXTENSIONS:
        xlabel_png_files_found.extend(glob.glob(os.path.join(args.input_xlabel_dir_conv, f"*{ext}")))
        xlabel_png_files_found.extend(glob.glob(os.path.join(args.input_xlabel_dir_conv, f"*{ext.upper()}")))

    if not xlabel_png_files_found: cli_logger.warning(f"No XLabel PNGs found in '{args.input_xlabel_dir_conv}'."); return
    cli_logger.info(f"Found {len(xlabel_png_files_found)} XLabel PNGs for batch conversion from XLabel to {args.to_format}.")

    aggregated_coco_output = None
    if args.to_format == "coco":
        aggregated_coco_output = {
            "info": {"description": f"XLabel Batch to COCO Export from dir: {args.input_xlabel_dir_conv}",
                     "version": xlabel_converters.REFINED_METADATA_VERSION, 
                     "year": datetime.datetime.strptime(xlabel_converters.coco_converter.CURRENT_DATE_TIME_UTC, "%Y-%m-%d %H:%M:%S").year,
                     "contributor": xlabel_converters.coco_converter.CURRENT_USER_LOGIN,
                     "date_created": xlabel_converters.coco_converter.CURRENT_DATE_TIME_UTC.replace(" ", "T") + "Z"},
            "licenses": [{"id": 1, "name": "Unknown", "url": ""}], "images": [], "categories": [], "annotations": []}
        global_image_id, global_annotation_id, global_max_category_id = 1, 1, 0
        global_category_map = {} 
    all_yolo_class_names = set()

    for png_path in xlabel_png_files_found:
        base_filename_no_ext = os.path.splitext(os.path.basename(png_path))[0]
        cli_logger.info(f"Processing XLabel PNG: {png_path}")
        try:
            metadata = xreader.read_xlabel_metadata_from_png(png_path)
            if not metadata: 
                cli_logger.warning(f"  No XLabel metadata found in '{png_path}'. Skipping."); 
                continue

            if args.to_format == "coco":
                img_entry, new_cat_entries, ann_entries, next_ann_id, updated_cat_map, updated_max_cat_id = \
                    xlabel_converters.xlabel_metadata_to_coco_parts(
                        metadata, global_image_id, global_category_map, global_max_category_id, global_annotation_id)
                aggregated_coco_output["images"].append(img_entry)
                aggregated_coco_output["categories"].extend(new_cat_entries) 
                aggregated_coco_output["annotations"].extend(ann_entries)
                
                global_image_id += 1; global_annotation_id = next_ann_id
                global_category_map = updated_cat_map; global_max_category_id = updated_max_cat_id
            
            elif args.to_format == "voc":
                output_voc_path = os.path.join(args.output_dir_conv, base_filename_no_ext + ".xml")
                voc_tree_root = xlabel_converters.xlabel_metadata_to_voc_xml_tree(metadata)
                ET.ElementTree(voc_tree_root).write(output_voc_path, encoding="utf-8", xml_declaration=True)
                cli_logger.info(f"  Converted to VOC XML: {output_voc_path}")
            
            elif args.to_format == "yolo":
                output_yolo_txt_path = os.path.join(args.output_dir_conv, base_filename_no_ext + ".txt")
                yolo_lines = xlabel_converters.xlabel_metadata_to_yolo_lines(metadata)
                with open(output_yolo_txt_path, 'w') as f:
                    for line in yolo_lines: f.write(line + "\n")
                current_classes = metadata.get("class_names", [])
                for cn in current_classes: all_yolo_class_names.add(cn)
                cli_logger.info(f"  Converted to YOLO TXT: {output_yolo_txt_path}")
            
            processed_count +=1 
        
        except (xlabel_converters.XLabelConversionError, xreader.XLabelError) as e:
            cli_logger.error(f"  XLabel Processing/Conversion Error for '{png_path}': {e}", exc_info=args.debug); error_count+=1
        except Exception as e:
            cli_logger.error(f"  Unexpected error converting '{png_path}': {e}", exc_info=args.debug); error_count+=1
    
    if args.to_format == "coco" and aggregated_coco_output:
        unique_categories = []; seen_category_ids = set()
        for category in aggregated_coco_output["categories"]:
            if category["id"] not in seen_category_ids: unique_categories.append(category); seen_category_ids.add(category["id"])
        aggregated_coco_output["categories"] = sorted(unique_categories, key=lambda c: c["id"])
        with open(args.output_coco, 'w') as f: json.dump(aggregated_coco_output, f, indent=args.indent)
        cli_logger.info(f"Aggregated COCO JSON saved to: {args.output_coco}")

    if args.to_format == "yolo" and args.yolo_class_names_output:
        yolo_master_class_file = args.yolo_class_names_output
        if not os.path.isabs(yolo_master_class_file) and args.output_dir_conv and os.path.isdir(args.output_dir_conv):
             yolo_master_class_file = os.path.join(args.output_dir_conv, os.path.basename(args.yolo_class_names_output))
        
        output_class_dir = os.path.dirname(yolo_master_class_file)
        if output_class_dir and not os.path.isdir(output_class_dir):
            try: os.makedirs(output_class_dir, exist_ok=True)
            except OSError as e: cli_logger.error(f"Could not create directory for YOLO class names file '{output_class_dir}': {e}")
        
        try:
            with open(yolo_master_class_file, 'w') as f:
                for name in sorted(list(all_yolo_class_names)): 
                    f.write(name + "\n")
            cli_logger.info(f"Aggregated YOLO class names saved to: {yolo_master_class_file}")
        except IOError as e:
            cli_logger.error(f"Could not write YOLO class names file to '{yolo_master_class_file}': {e}")
            
    cli_logger.info(f"\nBatch 'convert fromxlabel' summary: Successfully converted: {processed_count}, Errors: {error_count}.")
    if error_count > 0: sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="XLabel PNG Annotation Tool CLI: Create, read, and convert image annotations embedded in PNG files.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('--debug', action='store_true', help="Enable debug logging with detailed tracebacks.")
    subparsers = parser.add_subparsers(dest="command", required=True, help="Available commands. Use <command> --help for more details.")

    # --- Create command ---
    create_cmd_parser = subparsers.add_parser("create", help="Embed JSON metadata into PNG images to create XLabel PNGs.")
    create_subparsers = create_cmd_parser.add_subparsers(dest="create_mode", required=True, help="Creation mode: 'single' or 'batch'.")
    
    create_single_parser = create_subparsers.add_parser("single", help="Create one XLabel PNG from a single image and JSON metadata file.") 
    create_single_parser.add_argument("input_image_single", metavar="INPUT_IMAGE", help="Path to the original image (e.g., JPG, PNG).")
    create_single_parser.add_argument("json_metadata_single", metavar="JSON_METADATA", help="Path to the JSON file containing XLabel metadata.")
    create_single_parser.add_argument("output_xlabel_png_single", metavar="OUTPUT_XLABEL_PNG", help="Path to save the output XLabel PNG file (will be .png).")
    create_single_parser.add_argument("--overwrite", action="store_true", help="Overwrite output file if it already exists.")
    create_single_parser.set_defaults(func=handle_create_single)
    
    create_batch_parser = create_subparsers.add_parser("batch", help="Create XLabel PNGs for a directory of images and corresponding JSON files.") 
    create_batch_parser.add_argument("input_image_dir", metavar="INPUT_IMAGE_DIR", help="Directory containing input images.")
    create_batch_parser.add_argument("input_json_dir", metavar="INPUT_JSON_DIR", help="Directory containing corresponding JSON metadata files (matched by filename, excluding extension).")
    create_batch_parser.add_argument("output_xlabel_dir", metavar="OUTPUT_XLABEL_DIR", help="Directory to save output XLabel PNG files.")
    create_batch_parser.add_argument("--overwrite", action="store_true", help="Overwrite output files if they exist.")
    create_batch_parser.set_defaults(func=handle_create_batch)

    # --- Read command ---
    read_cmd_parser = subparsers.add_parser("read", help="Read XLabel metadata from PNGs. Can output to console or JSON sidecar files.")
    read_subparsers = read_cmd_parser.add_subparsers(dest="read_mode", required=True, help="Read mode: 'single' or 'batch'.")
    
    read_single_parser = read_subparsers.add_parser("single", help="Read XLabel metadata from a single XLabel PNG file.") 
    read_single_parser.add_argument("input_xlabel_png_single", metavar="INPUT_XLABEL_PNG", help="Path to the XLabel PNG file.")
    read_single_parser.add_argument("--output-json-single", "-o", metavar="OUTPUT_JSON", help="Optional: Path to save extracted metadata as a JSON file. If not provided, prints to console.")
    read_single_parser.add_argument("--indent", type=int, default=2, help="Indentation level for JSON output (default: 2).")
    read_single_parser.set_defaults(func=handle_read_single)
    
    read_batch_parser = read_subparsers.add_parser("batch", help="Read XLabel metadata from all XLabel PNGs in a directory, saving each as a separate JSON sidecar file.") 
    read_batch_parser.add_argument("input_xlabel_dir", metavar="INPUT_XLABEL_DIR", help="Directory of input XLabel PNG files.")
    read_batch_parser.add_argument("output_json_dir", metavar="OUTPUT_JSON_DIR", help="Directory to save output JSON sidecar files (one .json per .png).")
    read_batch_parser.add_argument("--indent", type=int, default=2, help="Indentation level for JSON output (default: 2).")
    read_batch_parser.set_defaults(func=handle_read_batch)

    # --- Convert command ---
    convert_parser = subparsers.add_parser("convert", help="Convert annotations between XLabel PNGs and other formats (COCO, VOC, YOLO).")
    convert_subparsers = convert_parser.add_subparsers(dest="convert_direction", required=True, help="Conversion flow: '2xlabel' (to XLabel) or 'fromxlabel' (from XLabel).")
    
    parser_2xlabel = convert_subparsers.add_parser("2xlabel", help="Convert other annotation formats (COCO, VOC, YOLO) to XLabel PNG(s).")
    parser_2xlabel.add_argument("from_format", choices=["coco", "voc", "yolo"], help="Source annotation format to convert from.")
    mode_2xlabel_group = parser_2xlabel.add_mutually_exclusive_group(required=True)
    mode_2xlabel_group.add_argument("--single", action="store_true", help="Process a single input image and its corresponding single annotation file.")
    mode_2xlabel_group.add_argument("--batch", action="store_true", help="Process a directory of input images and corresponding annotation files/directory.")
    parser_2xlabel.add_argument("--input-image", help="Path to the single input image file (for --single mode).") 
    parser_2xlabel.add_argument("--output-xlabel-png", help="Path for the single output XLabel PNG file (for --single mode).") 
    parser_2xlabel.add_argument("--input-voc", help="Path to the single input VOC XML file (for --single mode, if from_format=voc).") 
    parser_2xlabel.add_argument("--input-yolo-txt", help="Path to the single input YOLO TXT file (for --single mode, if from_format=yolo).") 
    parser_2xlabel.add_argument("--input-image-dir", help="Directory of input images (for --batch mode).") 
    parser_2xlabel.add_argument("--output-xlabel-dir", help="Output directory for generated XLabel PNGs (for --batch mode).") 
    parser_2xlabel.add_argument("--input-voc-dir", help="Directory of input VOC XML files (for --batch mode, if from_format=voc).") 
    parser_2xlabel.add_argument("--input-yolo-dir", help="Directory of input YOLO TXT files (for --batch mode, if from_format=yolo).") 
    parser_2xlabel.add_argument("--input-coco", help="Path to the input COCO JSON file (used if from_format=coco, for both --single and --batch).")
    parser_2xlabel.add_argument("--yolo-class-names", help="Path to the YOLO class names file (used if from_format=yolo, for both --single and --batch).")
    parser_2xlabel.add_argument("--overwrite", action="store_true", help="Overwrite output XLabel PNG(s) if they already exist.")
    def set_2xlabel_func_chooser_v2(args): args.func = handle_convert_2xlabel_batch if args.batch else handle_convert_2xlabel_single
    parser_2xlabel.set_defaults(func=set_2xlabel_func_chooser_v2)

    parser_fromxlabel = convert_subparsers.add_parser("fromxlabel", help="Convert XLabel PNG(s) to other annotation formats (COCO, VOC, YOLO).")
    parser_fromxlabel.add_argument("to_format", choices=["coco", "voc", "yolo"], help="Target annotation format to convert to.")
    mode_fromxlabel_group = parser_fromxlabel.add_mutually_exclusive_group(required=True)
    mode_fromxlabel_group.add_argument("--single", action="store_true", help="Process a single input XLabel PNG file.")
    mode_fromxlabel_group.add_argument("--batch", action="store_true", help="Process a directory of input XLabel PNG files.")
    parser_fromxlabel.add_argument("--input-xlabel-png-conv", help="Path to the single input XLabel PNG file (for --single mode).") 
    parser_fromxlabel.add_argument("--output-voc", help="Path for the single output VOC XML file (for --single mode, if to_format=voc).") 
    parser_fromxlabel.add_argument("--output-yolo-txt", help="Path for the single output YOLO TXT file (for --single mode, if to_format=yolo).") 
    parser_fromxlabel.add_argument("--input-xlabel-dir-conv", help="Directory of input XLabel PNG files (for --batch mode).") 
    parser_fromxlabel.add_argument("--output-dir-conv", help="Output directory for VOC XML or YOLO TXT files (for --batch mode, if to_format is voc or yolo).") 
    parser_fromxlabel.add_argument("--output-coco", help="Path for the output COCO JSON file (used if to_format=coco, for both --single and --batch [aggregated]).")
    parser_fromxlabel.add_argument("--yolo-class-names-output", help="Path for the YOLO class names output file (used if to_format=yolo, for both --single and --batch [aggregated]).")
    parser_fromxlabel.add_argument("--indent", type=int, default=2, help="Indentation level for COCO JSON output (default: 2).")
    def set_fromxlabel_func_chooser_v2(args): args.func = handle_convert_fromxlabel_batch if args.batch else handle_convert_fromxlabel_single
    parser_fromxlabel.set_defaults(func=set_fromxlabel_func_chooser_v2)
    
    args = parser.parse_args()
    
    if args.command == "convert" and ( (hasattr(args, 'from_format') and args.from_format == "coco") or \
                                       (hasattr(args, 'to_format') and args.to_format == "coco") ):
        current_utc_time_str = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        xlabel_converters.update_coco_creation_timestamp(current_utc_time_str)

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG) 
        for handler in logging.getLogger().handlers: 
            handler.setLevel(logging.DEBUG)
        cli_logger.info("Debug mode enabled with detailed tracebacks.")
    
    if hasattr(args, 'func') and callable(args.func):
        args.func(args)
    else: 
        cli_logger.error("Could not determine the action to perform. Please check your command.")
        if args.command == "create" and not hasattr(args, 'create_mode'): create_cmd_parser.print_help()
        elif args.command == "read" and not hasattr(args, 'read_mode'): read_cmd_parser.print_help()
        elif args.command == "convert" and not hasattr(args, 'convert_direction'): convert_parser.print_help()
        else: parser.print_help() 
        sys.exit(1)

if __name__ == "__main__":
    main()
