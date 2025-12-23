from src.cstructkit.annotations import (
    AnnotationPosition,
    AnnotationType,
    AnnotationData,
)

sample_annotation_data = [AnnotationData('a', 1, 0), AnnotationData('b', 4, 4)]


def test_place_annotations_above():
    fake_annotations = ['fieldA', 'fieldB']
    expected_placed = ['\t// fieldA\n\t', '\n\t// fieldB\n\t']
    actual_placed = AnnotationPosition.ABOVE.place_annotations(fake_annotations, 1)

    assert actual_placed == expected_placed


def test_place_annotations_above_places_newlines_appropriately():
    fake_annotations = ['fieldA', 'fieldB']
    placed = AnnotationPosition.ABOVE.place_annotations(fake_annotations, 1)

    assert not placed[0].startswith('\n')
    assert placed[-1].startswith('\n')


def test_place_annotations_indents_above():
    fake_annotations = ['fieldA', 'fieldB', 'fieldC']
    indentation_level = 2
    placed = AnnotationPosition.ABOVE.place_annotations(
        fake_annotations, indentation_level
    )

    for annotation in placed:
        assert annotation.removeprefix('\n').startswith('\t' * indentation_level)


def test_place_annotations_inline():
    fake_annotations = ['fieldA', 'fieldB']
    expected_annotations = ['\t/* fieldA */ ', '\t/* fieldB */ ']
    assert (
        AnnotationPosition.INLINE.place_annotations(fake_annotations, 1)
        == expected_annotations
    )


def test_place_annotations_indents_inline():
    fake_annotations = ['fieldA', 'fieldB']
    indentation_level = 3
    placed = AnnotationPosition.INLINE.place_annotations(
        fake_annotations, indentation_level
    )

    for annotation in placed:
        assert annotation.startswith('\t' * indentation_level)


def test_get_annotations_name():
    expected = ['A', 'B']
    assert AnnotationType.NAME.get_annotations(sample_annotation_data) == expected


def test_get_annotations_offset():
    expected = ['Offset: 0x00', 'Offset: 0x04']
    assert AnnotationType.OFFSET.get_annotations(sample_annotation_data) == expected


def test_get_annotations_size():
    expected = ['Size: 0x01', 'Size: 0x04']
    assert AnnotationType.SIZE.get_annotations(sample_annotation_data) == expected


def test_get_annotations_none():
    expected = ['', '']
    assert AnnotationType.NONE.get_annotations(sample_annotation_data) == expected
