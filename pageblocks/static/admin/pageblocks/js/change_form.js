/* global Vue */

window.addEventListener('load', () => {
  /* NOTE: Not the best way to handle this, but since the errors are already in the DOM, we can extract them before the editor initialises */
  function captureBlockEditorErrors() {
    const errors = [];
    for (const errorElem of document.querySelectorAll(".errorlist")) {
      let fieldId = null;
      for (let cls of errorElem.parentElement.classList) {
        const classParts = cls.split('-');
        if (classParts.length > 1 && classParts[0] === 'field') {
          fieldId = classParts[1];
        }
      }
      
      if (fieldId) {
        errors[fieldId] = []
        for (const errorElemLi of errorElem.querySelectorAll('li')) {
          if (errorElemLi.textContent.split(':')[0] === 'B') {
            errors[fieldId].push(errorElemLi.textContent.split(':'));
            errorElemLi.remove();
          }
        }
        if (errors[fieldId].length) {
          errorElem.parentElement.classList.remove('errors');
        }
      }
    }  
    return errors;
  }
  const blockEditorErrors = captureBlockEditorErrors(); 
 
  const FlagLookupMixin = {
    methods: {
      lookupFlag: function(language) {
        if (language === 'en') {
          return 'gb';
        }
        return language;
      }
    }
  };

  const TranslateMixin = {
    props: ['translations'],
    methods: {
      getText: function(id) {
        let c = this;
        while (c) {
          if (c.translations !== undefined && c._translations === undefined) {
            c._translations = JSON.parse(atob(c.translations));
          }
          if (c._translations !== undefined && c._translations[id]) {
            return c._translations[id];
          }
          c = c.$parent ? c.$parent : null;
        }
      }
    }
  };

  Vue.component('image-uploader', {
    template: `
      <div class="image-uploader">
        <div class="selector" v-if="!image" v-on:click.prevent="$refs.newImage.click()">
          <span>{{ getText('labelBtnAdd') }}</span>
        </div>
        <img v-if="image" :src="image" v-on:click.prevent="$refs.newImage.click()"/>
        <input v-on:change="handleImage" ref="newImage" class="new-image-btn" type="file" accept="image/*" style="display: none;"/>
      </div>
    `,
    mixins: [TranslateMixin],
    props: ['value'],
    data: function() {
      return {
        image: null
      };
    },
    mounted: function() {
      this.image = this.value !== undefined ? this.value : null;
    },
    methods: {
      handleImage(e) {
        this.readImage(e.target.files[0]).then((img) => {
          this.image = img;
          this.$emit('input', this.image);
          this.$emit('change', this.image);
        });
      },
      readImage(fileObject) {
        return new Promise((resolve) => {
          const reader = new FileReader();
          reader.onload = (e) => {
            resolve(e.target.result);
          };
          reader.readAsDataURL(fileObject);
        });
      },
      clear() {
        this.image = null;
        this.$emit('input', this.image);
        this.$emit('change', this.image);
      }  
    },
    watch: {
      value: function(nv) {
        this.image = nv !== undefined ? nv : null;
      }
    }  
  });

  Vue.component('page-block-editor-field', {
    template: `
    <div class="field" :class="hasError() ? 'errors' : ''">
      <label>{{ field.label }}<span class="small" v-if="field.required">*</span></label>
      <textarea v-if="field.input_type === 'textarea'" :required="field.required" :class="field.class" v-model="value" v-on:change="onValueChanged()"></textarea>
      <input v-if="field.input_type === 'text'" :type='field.input_type' :required="field.required" :class="field.class" v-model="value" v-on:change="onValueChanged()" />
      <block-editor
        v-if="field.input_type === 'blockstream'"
        v-model="value"
        :available-blocks="availableBlocks"
        v-on:change="onValueChanged()"
        :block-index="blockIndex"
        :input-name="inputName"
        :input-language="inputLanguage"></block-editor>
      <image-uploader
        v-if="field.input_type === 'image'"
        v-model="value"
        v-on:change="onValueChanged()"></image-uploader>
      <div v-if="hasError()" class="error">
        {{ getError() }}
      </div>
    </div>
    `,
    props: ['value', 'fieldId', 'field', 'availableBlocks', 'blockIndex', 'inputName', 'inputLanguage'],
    methods: {
      onValueChanged: function() {
        this.$emit('input', this.value);
        this.$emit('change', this.value);
      },
      hasError: function() {
        return this.getError() !== null;
      },
      getError: function() {
        if (this.$root.blockEditorErrors && this.inputName && this.inputLanguage && this.$root.blockEditorErrors[this.inputName]) {
          for (const err of this.$root.blockEditorErrors[this.inputName]) {
            if (err[1] === this.inputLanguage && err[2] === this.blockIndex.join(',') && err[3] == this.fieldId) {
              return err[err.length-1];
            }
          }
        }
        return null;
      }
    },
  });

  Vue.component('block-editor', {
    template: `
    <div class="block-editor">
      <div class="block" v-for="(block, index) in value" :key="'block-' + getBlockIndexKey(index)" v-if="availableBlocks[block.type] !== undefined">
        <div class="header row">
          <div class="bold">{{ getBlockTypeName(block.type) }} <span :class="'flag-icon flag-icon-'"></span></div>
          <div class="text-right buttons">
            <a href="javascript:;" :disabled="index <= 0" :class="{'disabled': index <= 0}"><i class="fa fas fa-caret-up"></i></a>
            <a href="javascript:;" :disabled="index + 1 >= value.length" :class="{'disabled': index + 1 >= value.length}"><i class="fa fas fa-caret-down"></i></a>

            <a v-on:click.prevent="deleteBlock(index)"><i class="fa fas fa-trash"></i></a>
          </div>
        </div>

        <page-block-editor-field 
          v-for="(field, fieldIndex) in Object.keys(availableBlocks[block.type].fields)" :key="'block-' + getBlockIndexKey(index) + '-' + fieldIndex"
          :field-id="field"
          :field="availableBlocks[block.type].fields[field]"
          v-model="block.data[field]"
          v-on:change="onValueChanged()"
          :available-blocks="availableBlocks"
          :block-index="getBlockIndex(index)"
          :input-name="inputName"
          :input-language="inputLanguage"
          >
        </page-block-editor-field>
      </div>

      <div class="buttons" style="display: flex; clear: both;" v-if="newBlockType">
        <div>
          <select class="form-control" v-model="newBlockType">
            <option v-for="(key, index) of Object.keys(availableBlocks)" :key="'block-' + getBlockIndexKey(index) + '-option'" :value="key">{{ availableBlocks[key].name }}</option>
          </select>
          <a class="button" v-on:click.prevent="addBlock(newBlockType)">{{ getText('labelBtnAdd') }} <i class="fa fas fa-plus"></i></a>
          <div class="small" v-if="newBlockType && newBlockType.description">
            {{ newBlockType.description }}
          </div>
        </div>
      </div>
    </div>
    `,
    props: ['value', 'availableBlocks', 'blockIndex', 'inputName', 'inputLanguage'],
    mixins: [TranslateMixin],
    data: function() {
      return {
        newBlockType: null
      }
    },
    mounted: function() {
      this.newBlockType = this.availableBlocks ? Object.keys(this.availableBlocks)[0] : null;
    },
    methods: {
      getBlockIndex: function(index) { 
        const parts = JSON.parse(JSON.stringify(this.blockIndex ? this.blockIndex : []));
        parts.push(index);
        return parts;
      },
      getBlockIndexKey: function(index) {
        return this.getBlockIndex(index).join('-');
      },
      onValueChanged: function() {
        this.$emit('input', this.value);
        this.$emit('change', this.value);
      },
      addBlock: function(blockType) {
        const initial = {};

        for (const fieldId of Object.keys(this.availableBlocks[blockType].fields)) {
          const field = this.availableBlocks[blockType].fields[fieldId];
          if (field.initial !== undefined) {
            initial[fieldId] = JSON.parse(JSON.stringify(field.initial));
          }
        }

        this.value.push({
          'type': blockType,
          'data': initial
        });
        this.onValueChanged();
      },
      getBlockTypeName: function(type) {
        return this.availableBlocks && this.availableBlocks[type] ? this.availableBlocks[type].name : this.getText('labelUnknown');
      },
      deleteBlock: function(index) {
        if (!window.confirm(this.getText('labelConfirmRemoveBlock'))) {
          return false;
        }

        if (index === 0 && this.value.length === 1) {
          this.value = []
        } else {
          this.value = this.value.splice(index, 1);
        }
        this.onValueChanged();
      }
    }
  });

  Vue.component('page-block-editor', {
    template: `
    <div class="page-block-editor">
      <input type="hidden" :name="name" v-model="jsonValue" />
      
      <fieldset v-for="language in Object.keys(languages)">
        <legend><span :class="'flag-icon flag-icon-' + lookupFlag(language)"></span> {{ languages[language] }}</legend>

        <div class="copy-buttons" v-if="Object.keys(languages).length > 1">
          {{ getText('labelCopyFrom') }}:
          <button class="button" v-for="(button_language, button_index) in Object.keys(languages)" v-if="language !== button_language"
              v-on:click.prevent="copyBlocks(button_language, language)">
            {{ button_language }}
          </button>
        </div>
      
        <block-editor
          v-model="blocks[language]"
          :available-blocks="availableBlocks"
          v-on:change="onFieldChanged()"
          :input-name="name"
          :input-language="language"></block-editor>

      </fieldset>

    </div>`,
    props: ['languages', 'initialValue', 'availableBlocks', 'name'],
    mixins: [FlagLookupMixin, TranslateMixin],
    data: function() {
      return {
        jsonValue: '[]',
        blocks: {}
      };
    },
    created: function() {

      this.languages = JSON.parse(atob(this.languages));
      for (let language of Object.keys(this.languages)) {
        this.blocks[language] = [];
      }

      this.availableBlocks = JSON.parse(atob(this.availableBlocks));
      if (this.initialValue) {
        this.jsonValue = this.initialValue;
      }
      this.parseFromJsonValue();
    },
    methods: {
      parseFromJsonValue: function() {
        try {
          this.blocks = JSON.parse(this.jsonValue);
        } catch (e) {
          console.error(e);
        }
      },
      parseToJsonValue: function() {
        this.jsonValue = JSON.stringify(this.blocks);
      },
      onFieldChanged: function() {
        this.parseToJsonValue();
      },
      copyBlocks: function(fromLanguage, toLanguage) {
        if (!window.confirm(this.getText('labelConfirmCopy'))) {
          return;
        }

        const newBlocks = [];
        for (let block of this.blocks[fromLanguage]) {
          const blockData = JSON.parse(JSON.stringify(block));
          delete blockData.id;
          newBlocks.push(blockData);
        }
        this.blocks[toLanguage] = newBlocks;
        this.parseToJsonValue();
      },
    }
  });

  Vue.component('multi-language-input', {
    template: `
    <div>
      <input type="hidden" :name="name" v-model="jsonValue" />

      <div v-for="language in Object.keys(languages)" :key="'ml-input-' + language" class="multi-language-row">
        <span :class="'flag-icon flag-icon-' + lookupFlag(language)"></span>
        <input type="text" class="form-control" v-model="values[language]" v-on:change="parseToJsonValue()"/>
      </div>
    </div>`,
    props: ['languages', 'name', 'initialValue'],
    data: function() {
      return {
        jsonValue: '{}',
        values: {}
      };
    },
    created: function() {
      this.languages = JSON.parse(atob(this.languages));
      if (this.initialValue) {
        this.jsonValue = this.initialValue;
      }
      this.parseFromJsonValue();
    },
    mixins: [
      FlagLookupMixin
    ],
    methods: {
      parseFromJsonValue: function() {
        let val = {};
        try {
          val = JSON.parse(this.jsonValue);
        } catch (e) {
          console.error(e);
        }

        for (let language of Object.keys(this.languages)) {
          this.values[language] = language in val ? val[language] : '';
        }
      },
      parseToJsonValue: function() {
        this.jsonValue = JSON.stringify(this.values);
      }
    }
  });

  new Vue({
    el: '#content',
    data: {
      blockEditorErrors: blockEditorErrors
    }
  });
});