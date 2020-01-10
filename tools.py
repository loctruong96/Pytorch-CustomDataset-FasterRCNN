import math 
import numpy as np 
import random 

# Code taken from 
# https://github.com/RockyXu66/Faster_RCNN_for_Open_Images_Dataset_Keras/blob/master/frcnn_train_vgg.ipynb


def base_size_calculator(h,w):
	# FOR RESNET
	# output = int((in_size - kernel_size + 2*(padding)) / stride) + 1
	output_size_conv = int((h - 7 + 2 * 3 )/ 2 ) + 1 , int((w - 7 + 2 * 3 )/ 2 ) + 1
	output_size_maxpool = int((output_size_conv[0] - 3 + 2 * 1 )/ 2 ) + 1 , int((output_size_conv[1] - 3 + 2 * 1 )/ 2 ) + 1

	output_size_layer1 = int((output_size_maxpool[0] - 1  )/ 1 ) + 1 , int((output_size_maxpool[1] - 1 )/ 1 ) + 1
	output_size_layer2 = int((output_size_layer1[0] - 3  + 2)/ 2 ) + 1 , int((output_size_layer1[1] - 3 + 2 )/ 2 ) + 1
	output_size_layer3 = int((output_size_layer2[0] - 3  + 2)/ 2 ) + 1 , int((output_size_layer2[1] - 3 + 2 )/ 2 ) + 1
	output_size_layer4 = output_size_layer3

	return output_size_layer4




def valid_anchors(anchor_sizes,anchor_ratios , downscale , output_width , resized_width , output_height , resized_height):
	anchor_boxes = {}
	n_anchratios = len(anchor_ratios) # 3
	for anchor_size_idx in range(len(anchor_sizes)):
		anchor_boxes[anchor_size_idx] = {}
		for anchor_ratio_idx in range(n_anchratios):
			anchor_boxes[anchor_size_idx][anchor_ratio_idx] = []
			# (Equation : 1, see figure)
			ratio_square_root = math.sqrt(anchor_ratios[anchor_ratio_idx])
			anchor_x = anchor_sizes[anchor_size_idx] / ratio_square_root
			anchor_y = anchor_sizes[anchor_size_idx] * ratio_square_root
			for ix in range(output_width):		
				# x-coordinates of the current anchor box	
				x1_anc = downscale * (ix + 0.5) - anchor_x / 2
				x2_anc = downscale * (ix + 0.5) + anchor_x / 2	
				# ignore boxes that go across image boundaries					
				if x1_anc < 0 or x2_anc > resized_width:
					continue
				for jy in range(output_height):
					# y-coordinates of the current anchor box
					y1_anc = downscale * (jy + 0.5) - anchor_y / 2
					y2_anc = downscale * (jy + 0.5) + anchor_y / 2
					# ignore boxes that go across image boundaries
					if y1_anc < 0 or y2_anc > resized_height:
						continue
					anchor_boxes[anchor_size_idx][anchor_ratio_idx].append((x1_anc , y1_anc , x2_anc,  y2_anc , ix , jy))
	return anchor_boxes
		


def iou(a, b):
    # (xmin,ymin,xmax,ymax)
    # invlaid boxes
    if a[0] >= a[2] or a[1] >= a[3] or b[0] >= b[2] or b[1] >= b[3]:
        return 0.0

    #intersection 
    x1 = max(a[0], b[0])
    y1 = max(a[1], b[1])
    x2 = min(a[2], b[2])
    y2 = min(a[3], b[3])

    if x2 - x1 <= 0  or y2 - y1 <=0 :
        intersection = 0 
    else:
        intersection = (x2 - x1) * (y2 - y1)

    area_a = (a[2] - a[0]) * (a[3] - a[1])
    area_b = (b[2] - b[0]) * (b[3] - b[1])
    union =  area_a + area_b - intersection

    if union <= 0 : 
        return 0.0
    else:
        return float(intersection) / float(union + 1e-6)


def calc_rpn(img_data, boxes , labels, anchor_sizes, anchor_ratios, valid_anchors , image_resize_size =(300,400), image_original_size=(600,800)): 
	num_anchors = len(anchor_sizes) * len(anchor_ratios) # 3x3=9
	n_anchratios = len(anchor_ratios) # 3
	(output_height , output_width) = base_size_calculator(image_resize_size[0], image_resize_size[1])

	y_is_box_label = np.zeros((output_height, output_width, num_anchors))
	y_rpn_regr = np.zeros((output_height, output_width, num_anchors * 4))
	

	num_bboxes = len(boxes)

	num_anchors_for_bbox = np.zeros(num_bboxes).astype(int)
	best_anchor_for_bbox = -1*np.ones((num_bboxes, 4)).astype(int)
	best_iou_for_bbox = np.zeros(num_bboxes).astype(np.float32)
	best_x_for_bbox = np.zeros((num_bboxes, 4)).astype(int)
	best_dx_for_bbox = np.zeros((num_bboxes, 4)).astype(np.float32)

	gta = np.array((boxes))

	for key1 in valid_anchors:
		for key2 in valid_anchors[key1]:
			for anchor_box in valid_anchors[key1][key2]: 
				anchor_ratio_idx = key2
				anchor_size_idx = key1

				x1_anc , y1_anc , x2_anc , y2_anc , ix , jy = anchor_box
				# bbox_type indicates whether an anchor should be a target
				# Initialize with 'negative'
				bbox_type = 'neg'
				# this is the best IOU for the (x,y) coord and the current anchor
				# note that this is different from the best IOU for a GT bbox
				best_iou_for_loc = 0.0
				
				# get IOU of the current GT box and the current anchor box
				for bbox_num in range(num_bboxes):
					curr_iou = iou([gta[bbox_num, 0], gta[bbox_num, 1], gta[bbox_num, 2], gta[bbox_num, 3]], [x1_anc, y1_anc, x2_anc, y2_anc])
					
					# calculate the regression targets if they will be needed
					if curr_iou > best_iou_for_bbox[bbox_num]  or curr_iou > args.rpn_max_overlap : 
						
						golden_center_x = (gta[bbox_num, 0] + gta[bbox_num, 2]) / 2.0
						golden_center_y = (gta[bbox_num, 1] + gta[bbox_num, 3]) / 2.0

						anchor_center_x = (x1_anc + x2_anc)/2.0
						anchor_center_y = (y1_anc + y2_anc)/2.0
						
						tx = (golden_center_x - anchor_center_x) / (x2_anc - x1_anc)
						ty = (golden_center_y - anchor_center_y) / (y2_anc - y1_anc)
						tw = np.log((gta[bbox_num, 2] - gta[bbox_num, 0]) / (x2_anc - x1_anc))
						th = np.log((gta[bbox_num, 3] - gta[bbox_num, 1]) / (y2_anc - y1_anc))

					
					if rev_label_map[labels[bbox_num]] != 'bg':	
						# all GT boxes should be mapped to an anchor box, so we keep track of which anchor box was best
						if curr_iou > best_iou_for_bbox[bbox_num]:
							best_anchor_for_bbox[bbox_num] = [jy, ix, anchor_ratio_idx, anchor_size_idx]
							best_iou_for_bbox[bbox_num] = curr_iou
							best_x_for_bbox[bbox_num,:] = [x1_anc, y1_anc , x2_anc, y2_anc]
							best_dx_for_bbox[bbox_num,:] = [tx, ty, tw, th]

						# we set the anchor to positive if the IOU is >0.7 (it does not matter if there was another better box, it just indicates overlap)
						if curr_iou > args.rpn_max_overlap:
							bbox_type = 'pos'
							num_anchors_for_bbox[bbox_num] += 1
							# we update the regression layer target if this IOU is the best for the current (x,y) and anchor position
							if curr_iou > best_iou_for_loc:
								best_iou_for_loc = curr_iou
								best_regr = (tx, ty, tw, th)

						# if the IOU is >0.3 and <0.7, it is ambiguous and no included in the objective
						if args.rpn_min_overlap < curr_iou and curr_iou < args.rpn_max_overlap:
							# gray zone between neg and pos
							if bbox_type != 'pos':
								bbox_type = 'neutral'


				# turn on or off outputs depending on IOUs
				if bbox_type == 'neg':
					y_is_box_label[jy, ix, anchor_ratio_idx + n_anchratios * anchor_size_idx] = -1
				elif bbox_type == 'neutral':
					y_is_box_label[jy, ix, anchor_ratio_idx + n_anchratios * anchor_size_idx] = 0
				elif bbox_type == 'pos':
					y_is_box_label[jy, ix, anchor_ratio_idx + n_anchratios * anchor_size_idx] = 1
					start = 4 * (anchor_ratio_idx + n_anchratios * anchor_size_idx)
					y_rpn_regr[jy, ix, start:start+4] = best_regr

						
	# we ensure that every bbox has at least one positive RPN region
	for idx in range(num_anchors_for_bbox.shape[0]):
		if num_anchors_for_bbox[idx] == 0:
			# no box with an IOU greater than zero ...
			if best_anchor_for_bbox[idx, 0] == -1:
				continue
			y_is_box_label[
			best_anchor_for_bbox[idx,0], 
			best_anchor_for_bbox[idx,1], 
			best_anchor_for_bbox[idx,2] + n_anchratios * best_anchor_for_bbox[idx,3]
			] = 1
			start = 4 * (best_anchor_for_bbox[idx,2] + n_anchratios * best_anchor_for_bbox[idx,3])
			y_rpn_regr[
				best_anchor_for_bbox[idx,0], best_anchor_for_bbox[idx,1], start:start+4] = best_dx_for_bbox[idx, :]


	num_regions = 500
	pos_locs = np.where(y_is_box_label == 1 )
	num_pos = len(pos_locs[0])

	neg_locs = np.where(y_is_box_label == -1 )
	num_neg =  len(neg_locs[0])

	# one issue is that the RPN has many more negative than positive regions, so we turn off some of the negative
	# regions. We also limit it to 256 regions.
	if num_pos > num_regions/2:
		non_valid_boxes  = random.sample(range( num_pos ), num_pos - num_regions/2)
		y_is_box_label[pos_locs[0][non_valid_boxes], pos_locs[1][non_valid_boxes], pos_locs[2][non_valid_boxes]] = 0 
		num_pos = num_regions/2

	if num_neg + num_pos > num_regions:
		non_valid_boxes = random.sample(range(num_neg), num_neg - num_pos)
		y_is_box_label[neg_locs[0][non_valid_boxes], neg_locs[1][non_valid_boxes], neg_locs[2][non_valid_boxes]] = 0 

	y_is_box_label = np.transpose(y_is_box_label, (2, 0, 1))
	y_is_box_label = np.expand_dims(y_is_box_label, axis=0)

	y_rpn_regr = np.transpose(y_rpn_regr, (2, 0, 1))
	y_rpn_regr = np.expand_dims(y_rpn_regr, axis=0)
	
	y_rpn_regr = np.concatenate([np.repeat(y_is_box_label, 4, axis=1), y_rpn_regr], axis=1)

	return np.copy(y_is_box_label), np.copy(y_rpn_regr), num_pos






def get_data(input_path , label_dict):
	"""Parse the data from annotation file
	Args:
		input_path: annotation file path
	Returns:
		all_data: list(filepath, width, height, list(bboxes))
	"""


	found_bg = False
	all_imgs = {}
	classes_count = {}
	class_mapping = {}
	visualise = True
	i = 1	


	with open(input_path,'r') as f:
		for line in f:
			# Print process
			sys.stdout.write('\r'+'idx=' + str(i))
			i += 1
			line_split = line.strip().split(',')

			# Make sure the info saved in annotation file matching the format (path_filename, x1, y1, x2, y2, class_name)
			# Note:
			#	One path_filename might has several classes (class_name)
			#	x1, y1, x2, y2 are the pixel value of the origial image, not the ratio value
			#	(x1, y1) top left coordinates; (x2, y2) bottom right coordinates
			#   x1,y1-------------------
			#	|						|
			#	|						|
			#	|						|
			#	|						|
			#	---------------------x2,y2

			(filename,x1,y1,x2,y2,class_name) = line_split

			if class_name not in classes_count:
				classes_count[class_name] = 1
			else:
				classes_count[class_name] += 1

			if class_name not in class_mapping:
				if class_name == 'bg' and found_bg == False:
					print('Found class name with special name bg. Will be treated as a background region (this is usually for hard negative mining).')
					found_bg = True
				class_mapping[class_name] = len(class_mapping)

			if filename not in all_imgs:
				all_imgs[filename] = {}
				
				img = cv2.imread(filename)
				(rows,cols) = img.shape[:2]
				all_imgs[filename]['filepath'] = filename
				all_imgs[filename]['width'] = cols
				all_imgs[filename]['height'] = rows
				all_imgs[filename]['bboxes'] = []
				# if np.random.randint(0,6) > 0:
				# 	all_imgs[filename]['imageset'] = 'trainval'
				# else:
				# 	all_imgs[filename]['imageset'] = 'test'

			all_imgs[filename]['bboxes'].append({'class': class_name, 'x1': int(x1), 'x2': int(x2), 'y1': int(y1), 'y2': int(y2)})


		all_data = []
		for key in all_imgs:
			all_data.append(all_imgs[key])
		
		# make sure the bg class is last in the list
		if found_bg:
			if class_mapping['bg'] != len(class_mapping) - 1:
				key_to_switch = [key for key in class_mapping.keys() if class_mapping[key] == len(class_mapping)-1][0]
				val_to_switch = class_mapping['bg']
				class_mapping['bg'] = len(class_mapping) - 1
				class_mapping[key_to_switch] = val_to_switch
		
		return all_data, classes_count, class_mapping





# import torchvision.transforms.functional as FT






def photometric_distort(image):
    """
    Distort brightness, contrast, saturation, and hue, each with a 50% chance, in random order.
    :param image: image, a PIL Image
    :return: distorted image
    """
    new_image = image

    distortions = [FT.adjust_brightness,
                   FT.adjust_contrast,
                   FT.adjust_saturation,
                   FT.adjust_hue]

    random.shuffle(distortions)

    for d in distortions:
        if random.random() < 0.5:
            if d.__name__ is 'adjust_hue':
                # Caffe repo uses a 'hue_delta' of 18 - we divide by 255 because PyTorch needs a normalized value
                adjust_factor = random.uniform(-18 / 255., 18 / 255.)
            else:
                # Caffe repo uses 'lower' and 'upper' values of 0.5 and 1.5 for brightness, contrast, and saturation
                adjust_factor = random.uniform(0.5, 1.5)

            # Apply this distortion
            new_image = d(new_image, adjust_factor)

    return new_image








def transform(image, boxes, labels, difficulties, split):
    """
    Apply the transformations above.
    :param image: image, a PIL Image
    :param boxes: bounding boxes in boundary coordinates, a tensor of dimensions (n_objects, 4)
    :param labels: labels of objects, a tensor of dimensions (n_objects)
    :param difficulties: difficulties of detection of these objects, a tensor of dimensions (n_objects)
    :param split: one of 'TRAIN' or 'TEST', since different sets of transformations are applied
    :return: transformed image, transformed bounding box coordinates, transformed labels, transformed difficulties
    """
    assert split in {'TRAIN', 'TEST'}

    # Mean and standard deviation of ImageNet data that our base VGG from torchvision was trained on
    # see: https://pytorch.org/docs/stable/torchvision/models.html
    mean = [0.485, 0.456, 0.406]
    std = [0.229, 0.224, 0.225]

    new_image = image
    new_boxes = boxes
    new_labels = labels
    new_difficulties = difficulties
    # Skip the following operations if validation/evaluation
    if split == 'TRAIN':
        # A series of photometric distortions in random order, each with 50% chance of occurrence, as in Caffe repo
        new_image = photometric_distort(new_image)

        # Convert PIL image to Torch tensor
        new_image = FT.to_tensor(new_image)

        # Expand image (zoom out) with a 50% chance - helpful for training detection of small objects
        # Fill surrounding space with the mean of ImageNet data that our base VGG was trained on
        if random.random() < 0.5:
            new_image, new_boxes = expand(new_image, boxes, filler=mean)

        # Randomly crop image (zoom in)
        new_image, new_boxes, new_labels, new_difficulties = random_crop(new_image, new_boxes, new_labels,
                                                                         new_difficulties)

        # Convert Torch tensor to PIL image
        new_image = FT.to_pil_image(new_image)

        # Flip image with a 50% chance
        if random.random() < 0.5:
            new_image, new_boxes = flip(new_image, new_boxes)

    # Resize image to (300, 300) - this also converts absolute boundary coordinates to their fractional form
    new_image, new_boxes = resize(new_image, new_boxes, dims=(300, 300))

    # Convert PIL image to Torch tensor
    new_image = FT.to_tensor(new_image)

    # Normalize by mean and standard deviation of ImageNet data that our base VGG was trained on
    new_image = FT.normalize(new_image, mean=mean, std=std)

    return new_image, new_boxes, new_labels, new_difficulties



from PIL import Image , ImageEnhance


def flip(image, boxes):
    # Flip image
    new_image = image.transpose(Image.FLIP_LEFT_RIGHT)
    # new_image = FT.hflip(image)
    # Flip boxes
    boxes = [ [image.width - cord -1 if i % 2 ==0 else cord for i,cord in enumerate(box)  ] for box in boxes]
    boxes = [ [box[2] ,box[1] , box[0], box[3]] for box in boxes]
    return new_image, boxes





class Transform(object):
 	"""docstring for Transform"""
 	def __init__(self,  train):
 		super(Transform, self).__init__()
 		self.train = train 
 		
 	def apply_transform(self, image, boxes, labels resize_size = None ) :
 		if resize_size:
 			orig_size = image.size
 			# (4032, 3024)
 			image = image.resize(resize_size)
 			boxes= [ [cord * resize_size[i % 2] / orig_size[i % 2] for i,cord in enumerate(box) ] for box in boxes]

 		if self.train : 
 			if random.random() < 0.5:
 				image , boxes = flip(image, boxes)
 			
 			if random.random() < 0.5:
 				enhancer = ImageEnhance.Sharpness(image)
 				image = enhancer.enhance(1/8)
 			
 			if random.random() < 0.5:
 				factor  = random.random() 
 				if factor > 0.5: 
	 				enhancer = ImageEnhance.Brightness(image)
	 				image = enhancer.enhance(factor)

 				
 				

 		