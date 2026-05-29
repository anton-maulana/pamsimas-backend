from fastcrud import FastCRUD

from ..models.image import Image
from ..schemas.image import ImageCreateInternal, ImageDelete, ImageRead, ImageUpdate, ImageUpdateInternal

CRUDImage = FastCRUD[Image, ImageCreateInternal, ImageUpdate, ImageUpdateInternal, ImageDelete, ImageRead]
crud_images = CRUDImage(Image)
