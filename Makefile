USER ?= mikhail0vvlad
# кроп подобран под source-photo.png: голова и плечи
CROP ?= 0.29,0.1875,0.625,0.4375

.PHONY: all heatmap card portrait preview

all: heatmap card portrait

heatmap:
	python scripts/fetch_contributions.py $(USER)
	python scripts/render_heatmap_svg.py

card:
	python scripts/make_info_card.py

portrait:
	CROP=$(CROP) python scripts/prep_photo.py source-photo.png source-prepped.png
	python scripts/make_ascii_svg.py

preview:
	STATIC=1 python scripts/make_info_card.py
	STATIC=1 python scripts/make_ascii_svg.py
	STATIC=1 python scripts/render_heatmap_svg.py
