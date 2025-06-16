import argparse
import json
import sys
import os
import logging
from PIL import Image # For getting image dimensions in some cases

# Import functions from our modules
import xcreator
import xreader
import xlabel_converters

# Import custom exceptions (assuming they are defined in the imported modules or a common place)
# If they are defined in each module, we might need to import them specifically or define them here.
# For now, let's assume they are accessible via the module names.
# e.g., xreader.XLabelFormatError, xlabel_converters.XLabelConversionError

# --- Setup Global Logger for CLI ---
# The individual modules (xreader, xcreator, xlabel_converters) will use their own loggers
# (e.g., logging.getLogger(__name__)).
# Here, we configure the root logger or a specific CLI logger for overall CLI messages.
# This basicConfig will apply to loggers from other modules as well if they don't have specific handlers.
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
# For more fine-grained control, get a specific logger for the CLI:
cli_logger = logging.getLogger("xlabel_cli")
# cli_logger.setLevel(logging.INFO) # if basicConfig wasn't called or to override


def handle_create(args):
    """Handles the 'create' command."""
    try:
        with open(args.json_metadata, 'r') as f:
            metadata = json.load(f)
        
        # The xcreator module now handles its own validation and raises XLabelFormatError
        # It also sets the correct xlabel_version internally.
        xcreator.add_xlabel_metadata_to_png(args.input_image, args.output_xlabel_png, metadata, args.overwrite)
        cli_logger.info(f"Successfully created XLabel PNG: {args.output_xlabel_png}")
    except FileNotFoundError as e:
        cli_logger.error(f"Error: File not found - {e}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        cli_logger.error(f"Error: Invalid JSON metadata file '{args.json_metadata}': {e}")
        sys.exit(1)
    except xcreator.XLabelFormatError as e: # Catch specific format error from xcreator
        cli_logger.error(f"Metadata Format Error: {e}")
        sys.exit(1)
    except xcreator.XLabelError as e: # Catch other XLabel errors from xcreator
        cli_logger.error(f"XLabel Creation Error: {e}")
        sys.exit(1)
    except FileExistsError as e: # Caught if overwrite is False and file exists
        cli_logger.error(f"Output Error: {e}")
        sys.exit(1)
    except Exception as e:
        cli_logger.error(f"An unexpected error occurred during 'create': {e}", exc_info=args.debug)
        sys.exit(1)

def handle_read(args):
    """Handles the 'read' command."""
    try:
        metadata = xreader.read_xlabel_metadata_from_png(args.input_xlabel_png)
        if metadata:
            if args.output_json:
                with open(args.output_json, 'w') as f:
                    json.dump(metadata, f, indent=args.indent)
                cli_logger.info(f"Metadata extracted to: {args.output_json}")
            else:
                print(json.dumps(metadata, indent=args.indent)) # Print to stdout
        else:
            # xreader.read_xlabel_metadata_from_png might return None if chunk not found but no error.
            # If it always raises an exception on failure, this 'else' might not be reached.
            cli_logger.warning(f"No XLabel metadata found or extracted from '{args.input_xlabel_png}'.")
            # Consider if this case should be an error (sys.exit(1))
            
    except FileNotFoundError as e:
        cli_logger.error(f"Error: Input XLabel PNG not found - {e}")
        sys.exit(1)
    except xreader.XLabelFormatError as e:
        cli_logger.error(f"XLabel Format Error reading PNG: {e}")
        sys.exit(1)
    except xreader.XLabelVersionError as e: # If xreader defines/raises this
        cli_logger.error(f"XLabel Version Error: {e}")
        sys.exit(1)
    except xreader.XLabelError as e: # Catch other XLabel errors from xreader
        cli_logger.error(f"XLabel Read Error: {e}")
        sys.exit(1)
    except Exception as e:
        cli_logger.error(f"An unexpected error occurred during 'read': {e}", exc_info=args.debug)
        sys.exit(1)

def handle_convert(args):
    """Handles the 'convert' command."""
    try:
        # --- Convert FROM other formats TO XLabel PNG ---
        if args.direction == "2xlabel":
            if not args.input_image:
                cli_logger.error("Error: --input-image is required when converting to XLabel PNG (2xlabel).")
                sys.exit(1)
            if not args.output_xlabel_png:
                 cli_logger.error("Error: --output-xlabel-png is required when converting to XLabel PNG (2xlabel).")
                 sys.exit(1)

            metadata = None
            img_width, img_height = None, None
            try:
                with Image.open(args.input_image) as img:
                    img_width, img_height = img.width, img.height
            except FileNotFoundError:
                cli_logger.error(f"Error: Input image '{args.input_image}' not found for size determination.")
                sys.exit(1)
            except Exception as e:
                cli_logger.error(f"Error opening input image '{args.input_image}' to get dimensions: {e}")
                sys.exit(1)

            if args.from_format == "coco":
                if not args.input_coco: cli_logger.error("Error: --input-coco is required for COCO to XLabel conversion."); sys.exit(1)
                # coco_to_xlabel_metadata expects image filename that's IN the COCO json
                # We use the basename of the provided input_image path for this.
                image_filename_for_coco = os.path.basename(args.input_image)
                metadata = xlabel_converters.coco_to_xlabel_metadata(args.input_coco, image_filename_for_coco)
            elif args.from_format == "voc":
                if not args.input_voc: cli_logger.error("Error: --input-voc is required for VOC to XLabel conversion."); sys.exit(1)
                metadata = xlabel_converters.voc_to_xlabel_metadata(args.input_voc)
            elif args.from_format == "yolo":
                if not args.input_yolo_txt: cli_logger.error("Error: --input-yolo-txt is required."); sys.exit(1)
                if not args.yolo_class_names: cli_logger.error("Error: --yolo-class-names is required."); sys.exit(1)
                yolo_img_filename = os.path.basename(args.input_image) # Use actual image filename
                metadata = xlabel_converters.yolo_to_xlabel_metadata(args.input_yolo_txt, args.yolo_class_names, img_width, img_height, yolo_img_filename)
            
            if metadata:
                # Ensure image_properties in metadata match the actual input_image provided
                metadata["image_properties"]["filename"] = os.path.basename(args.input_image)
                metadata["image_properties"]["width"] = img_width
                metadata["image_properties"]["height"] = img_height
                
                xcreator.add_xlabel_metadata_to_png(args.input_image, args.output_xlabel_png, metadata, args.overwrite)
                cli_logger.info(f"Successfully converted {args.from_format} to XLabel PNG: {args.output_xlabel_png}")
            else:
                # This path should ideally not be reached if converters raise exceptions
                cli_logger.error(f"Conversion from {args.from_format} failed: No metadata generated.")
                sys.exit(1)

        # --- Convert FROM XLabel PNG TO other formats ---
        elif args.direction == "fromxlabel":
            if not args.input_xlabel_png:
                cli_logger.error("Error: --input-xlabel-png is required when converting from XLabel PNG.")
                sys.exit(1)
            
            metadata = xreader.read_xlabel_metadata_from_png(args.input_xlabel_png)
            if not metadata:
                # This case might mean chunk not found and xreader returned None, or an error occurred.
                # If xreader always raises, this specific 'if not metadata' might not be hit without prior exception.
                cli_logger.error(f"Failed to read metadata from XLabel PNG '{args.input_xlabel_png}'. Cannot convert.")
                sys.exit(1)

            if args.to_format == "coco":
                if not args.output_coco: cli_logger.error("Error: --output-coco is required."); sys.exit(1)
                coco_data = xlabel_converters.xlabel_metadata_to_coco_json_structure(metadata)
                with open(args.output_coco, 'w') as f: json.dump(coco_data, f, indent=args.indent)
                cli_logger.info(f"Converted XLabel PNG to COCO JSON: {args.output_coco}")
            elif args.to_format == "voc":
                if not args.output_voc: cli_logger.error("Error: --output-voc is required."); sys.exit(1)
                voc_tree_root = xlabel_converters.xlabel_metadata_to_voc_xml_tree(metadata)
                voc_tree = ET.ElementTree(voc_tree_root)
                # ET.indent(voc_tree, space="\t", level=0) # For pretty printing XML, Python 3.9+
                voc_tree.write(args.output_voc, encoding="utf-8", xml_declaration=True)
                cli_logger.info(f"Converted XLabel PNG to VOC XML: {args.output_voc}")
            elif args.to_format == "yolo":
                if not args.output_yolo_txt: cli_logger.error("Error: --output-yolo-txt is required."); sys.exit(1)
                if not args.yolo_class_names_output: cli_logger.error("Error: --yolo-class-names-output is required for YOLO export (to save class list)."); sys.exit(1)
                yolo_lines = xlabel_converters.xlabel_metadata_to_yolo_lines(metadata)
                with open(args.output_yolo_txt, 'w') as f:
                    for line in yolo_lines: f.write(line + "\n")
                with open(args.yolo_class_names_output, 'w') as f:
                    for name in metadata.get("class_names",[]): f.write(name + "\n")
                cli_logger.info(f"Converted XLabel PNG to YOLO: {args.output_yolo_txt} and {args.yolo_class_names_output}")
        else:
            cli_logger.error(f"Invalid conversion direction: {args.direction}") # Should be caught by argparse choices
            sys.exit(1)

    except FileNotFoundError as e:
        cli_logger.error(f"File Not Found Error during 'convert': {e}")
        sys.exit(1)
    except (xreader.XLabelError, xcreator.XLabelError, xlabel_converters.XLabelConversionError, xlabel_converters.XLabelFormatError) as e:
        # Catch all our custom XLabel related errors from the modules
        cli_logger.error(f"XLabel Processing Error: {e}")
        sys.exit(1)
    except ET.ParseError as e: # Specifically for XML issues not caught internally by converter
        cli_logger.error(f"XML Parsing Error: {e}")
        sys.exit(1)
    except Exception as e:
        cli_logger.error(f"An unexpected error occurred during 'convert': {e}", exc_info=args.debug)
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="XLabel PNG Annotation Tool CLI")
    parser.add_argument('--debug', action='store_true', help="Enable debug logging including tracebacks for unexpected errors.")
    subparsers = parser.add_subparsers(dest="command", required=True, help="Available commands")

    # --- Create command ---
    create_parser = subparsers.add_parser("create", help="Embed JSON metadata into a PNG image.")
    create_parser.add_argument("input_image", help="Path to the original image (e.g., JPG, PNG).")
    create_parser.add_argument("json_metadata", help="Path to the JSON file containing XLabel metadata.")
    create_parser.add_argument("output_xlabel_png", help="Path to save the output XLabel PNG file.")
    create_parser.add_argument("--overwrite", action="store_true", help="Overwrite output file if it exists.")
    create_parser.set_defaults(func=handle_create)

    # --- Read command ---
    read_parser = subparsers.add_parser("read", help="Read XLabel metadata from an XLabel PNG.")
    read_parser.add_argument("input_xlabel_png", help="Path to the XLabel PNG file.")
    read_parser.add_argument("--output-json", "-o", help="Optional: Path to save the extracted metadata as JSON.")
    read_parser.add_argument("--indent", type=int, default=2, help="Indentation for JSON output (default: 2).")
    read_parser.set_defaults(func=handle_read)

    # --- Convert command ---
    convert_parser = subparsers.add_parser("convert", help="Convert annotations between XLabel PNG and other formats.")
    convert_parser.add_argument("direction", choices=["2xlabel", "fromxlabel"], help="'2xlabel': Convert other format to XLabel PNG. 'fromxlabel': Convert XLabel PNG to other format.")
    
    # Options for converting TO XLabel PNG
    convert_parser.add_argument("--from-format", choices=["coco", "voc", "yolo"], help="Source format when direction is '2xlabel'.")
    convert_parser.add_argument("--input-image", help="Path to the original image (Required for '2xlabel').")
    convert_parser.add_argument("--input-coco", help="Path to input COCO JSON file (for 'coco' to XLabel).")
    convert_parser.add_argument("--input-voc", help="Path to input VOC XML file (for 'voc' to XLabel).")
    convert_parser.add_argument("--input-yolo-txt", help="Path to input YOLO TXT file (for 'yolo' to XLabel).")
    convert_parser.add_argument("--yolo-class-names", help="Path to YOLO class names file (required for 'yolo' to XLabel).")
    convert_parser.add_argument("--output-xlabel-png", help="Path to save the output XLabel PNG (for '2xlabel').")
    convert_parser.add_argument("--overwrite", action="store_true", help="Overwrite output XLabel PNG if it exists.")

    # Options for converting FROM XLabel PNG
    convert_parser.add_argument("--to-format", choices=["coco", "voc", "yolo"], help="Target format when direction is 'fromxlabel'.")
    convert_parser.add_argument("--input-xlabel-png", help="Path to the input XLabel PNG (for 'fromxlabel' or if used as source for '2xlabel' image properties).")
    convert_parser.add_argument("--output-coco", help="Path to save output COCO JSON file.")
    convert_parser.add_argument("--output-voc", help="Path to save output VOC XML file.")
    convert_parser.add_argument("--output-yolo-txt", help="Path to save output YOLO TXT file.")
    convert_parser.add_argument("--yolo-class-names-output", help="Path to save YOLO class names file (for XLabel to 'yolo').")
    convert_parser.add_argument("--indent", type=int, default=2, help="Indentation for COCO JSON output (default: 2).")
    convert_parser.set_defaults(func=handle_convert)
    
    args = parser.parse_args()
    
    if args.debug:
        # If debug is enabled, set root logger level to DEBUG to get more detailed logs from all modules
        logging.getLogger().setLevel(logging.DEBUG) # Get root logger
        cli_logger.info("Debug mode enabled.")

    args.func(args)

if __name__ == "__main__":
    main()